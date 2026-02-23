"""Tree of Thoughts engine — Data Plane component.

Implements beam-search over a ThoughtTree with deterministic pruning,
scoring, and a single-backtrack fallback when all beams are pruned.

All randomness is seeded; no LLM calls.  Thought generation uses
deterministic string permutation of the initial prompt tokens.
"""

from __future__ import annotations

import json
import time
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any

from thalos_prime.reasoning.schema import (
    REASONING_SCHEMA_VERSION,
    ThoughtNode,
    ThoughtStatus,
    ThoughtTree,
)
from thalos_prime.reasoning.thought_scorer import ThoughtScorer

if TYPE_CHECKING:
    from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph

# Default parameters
_DEFAULT_MAX_DEPTH: int = 5
_DEFAULT_BEAM_WIDTH: int = 3
_DEFAULT_SCORE_THRESHOLD: float = 0.3
# Early-termination threshold: nodes scoring at or above this become TERMINAL immediately
_EARLY_TERMINAL_SCORE: float = 0.9


def _compute_node_id(parent_id: str | None, thought_text: str, depth: int) -> str:
    """Stable SHA-256 id for a ThoughtNode."""
    raw = f"{parent_id or ''}:{thought_text}:{depth}"
    return sha256(raw.encode()).hexdigest()


def _derive_node_seed(base_seed: int, depth: int, branch_index: int) -> int:
    """Derive a node-specific seed deterministically."""
    return base_seed ^ (depth * 1_000_003) ^ branch_index


def _expand_thought(parent_text: str, node_seed: int, branch_index: int) -> str:
    """Generate a deterministic child thought from a parent thought text.

    Uses seed-based word-list rotation.  No LLM.
    """
    words = parent_text.split()
    if not words:
        return parent_text
    rotate = (node_seed + branch_index) % len(words)
    rotated = words[rotate:] + words[:rotate]
    return " ".join(rotated)


class TreeOfThoughts:
    """Data Plane engine implementing Tree of Thoughts with beam search.

    Algorithm (breadth-first with beam):
        1. Root: create ThoughtNode(depth=0, text=initial_prompt).
        2. Expand: for each active leaf, generate beam_width child thoughts.
        3. Score: score each child with ThoughtScorer.
        4. Select: keep top beam_width by score; prune remainder.
        5. Terminate: mark nodes at max_depth as TERMINAL (guaranteed);
           or early-terminate if score >= _EARLY_TERMINAL_SCORE.
        6. Backtrack: if all active nodes pruned before max_depth,
           re-activate best pruned node from current depth (once per run).
        7. Result: return the TERMINAL node with highest score.
    """

    def __init__(
        self,
        max_depth: int = _DEFAULT_MAX_DEPTH,
        beam_width: int = _DEFAULT_BEAM_WIDTH,
        score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
        log_path: Path | None = None,
    ) -> None:
        """Initialize the Tree of Thoughts engine.

        Args:
            max_depth: Maximum reasoning depth.
            beam_width: Number of branches per depth level.
            score_threshold: Prune nodes with score < threshold.
            log_path: Optional JSONL log file path.

        """
        self.max_depth = max_depth
        self.beam_width = beam_width
        self.score_threshold = score_threshold
        self._log_path = log_path
        self._scorer = ThoughtScorer()

    def run(
        self,
        initial_prompt: str,
        seed: int,
        graph: KnowledgeGraph | None = None,
    ) -> ThoughtNode:
        """Run Tree of Thoughts exploration.

        Args:
            initial_prompt: The initial query or reasoning prompt.
            seed: Deterministic seed (from ControlPlane).
            graph: Optional KnowledgeGraph for graph-aware scoring.

        Returns:
            The best TERMINAL ThoughtNode.

        """
        root_id = _compute_node_id(None, initial_prompt, 0)
        root_score = self._scorer.score(initial_prompt, graph)
        root = ThoughtNode(
            id=root_id,
            parent_id=None,
            depth=0,
            thought_text=initial_prompt,
            score=root_score,
            status=ThoughtStatus.ACTIVE,
            seed=seed,
        )
        tree = ThoughtTree(root=root, seed=seed)
        tree.add_node(root)

        active_ids = [root_id]
        all_pruned_by_depth: dict[int, list[ThoughtNode]] = {}
        did_backtrack = False

        for depth in range(1, self.max_depth + 1):
            if not active_ids:
                break
            active_ids, did_backtrack = self._process_depth(
                depth, active_ids, tree, seed, graph, all_pruned_by_depth, did_backtrack
            )

        return self._pick_best(tree)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_depth(
        self,
        depth: int,
        active_ids: list[str],
        tree: ThoughtTree,
        seed: int,
        graph: KnowledgeGraph | None,
        all_pruned_by_depth: dict[int, list[ThoughtNode]],
        did_backtrack: bool,
    ) -> tuple[list[str], bool]:
        """Expand, score, and select nodes for one depth level.

        Returns:
            Tuple of (next_active_ids, did_backtrack).

        """
        candidates = self._expand(active_ids, depth, tree, seed, graph)
        if not candidates:
            return [], did_backtrack

        candidates.sort(key=lambda n: (-n.score, n.id))
        selected = candidates[: self.beam_width]
        overflow = candidates[self.beam_width :]

        for node in overflow:
            node.status = ThoughtStatus.PRUNED
            tree.add_node(node, node.parent_id)
            all_pruned_by_depth.setdefault(depth, []).append(node)
            self._log({"event": "pruned", "node_id": node.id, "score": node.score, "depth": depth})

        # At max_depth always mark selected as TERMINAL (guaranteed termination)
        if depth == self.max_depth:
            for node in selected:
                node.status = ThoughtStatus.TERMINAL
                tree.add_node(node, node.parent_id)
                self._log({"event": "terminal", "node_id": node.id, "score": node.score})
            return [], did_backtrack

        # Apply score threshold and classify surviving nodes
        surviving, threshold_pruned = self._classify(selected, depth, all_pruned_by_depth)
        for node in threshold_pruned:
            tree.add_node(node, node.parent_id)
        for node in surviving:
            tree.add_node(node, node.parent_id)

        next_active: list[str] = []
        for node in surviving:
            if node.score >= _EARLY_TERMINAL_SCORE:
                node.status = ThoughtStatus.TERMINAL
                self._log({"event": "terminal", "node_id": node.id, "score": node.score})
            else:
                next_active.append(node.id)

        if not next_active and not did_backtrack:
            next_active, did_backtrack = self._backtrack(depth, all_pruned_by_depth)

        return next_active, did_backtrack

    def _expand(
        self,
        active_ids: list[str],
        depth: int,
        tree: ThoughtTree,
        seed: int,
        graph: KnowledgeGraph | None,
    ) -> list[ThoughtNode]:
        """Generate all candidate child nodes for the active set."""
        candidates: list[ThoughtNode] = []
        for parent_id in active_ids:
            parent_node = tree.nodes[parent_id]
            if parent_node.status == ThoughtStatus.TERMINAL:
                continue
            for branch_idx in range(self.beam_width):
                node_seed = _derive_node_seed(seed, depth, branch_idx)
                thought_text = _expand_thought(parent_node.thought_text, node_seed, branch_idx)
                node_id = _compute_node_id(parent_id, thought_text, depth)
                score = self._scorer.score(thought_text, graph)
                candidates.append(
                    ThoughtNode(
                        id=node_id,
                        parent_id=parent_id,
                        depth=depth,
                        thought_text=thought_text,
                        score=score,
                        status=ThoughtStatus.PENDING,
                        seed=node_seed,
                    )
                )
        return candidates

    def _classify(
        self,
        selected: list[ThoughtNode],
        depth: int,
        all_pruned_by_depth: dict[int, list[ThoughtNode]],
    ) -> tuple[list[ThoughtNode], list[ThoughtNode]]:
        """Apply score threshold; return (surviving, threshold_pruned)."""
        surviving: list[ThoughtNode] = []
        threshold_pruned: list[ThoughtNode] = []
        for node in selected:
            if node.score < self.score_threshold:
                node.status = ThoughtStatus.PRUNED
                all_pruned_by_depth.setdefault(depth, []).append(node)
                threshold_pruned.append(node)
                self._log({"event": "threshold_pruned", "node_id": node.id, "score": node.score})
            else:
                node.status = ThoughtStatus.ACTIVE
                surviving.append(node)
        return surviving, threshold_pruned

    def _backtrack(
        self,
        depth: int,
        all_pruned_by_depth: dict[int, list[ThoughtNode]],
    ) -> tuple[list[str], bool]:
        """Re-activate best pruned node from current depth (once per run)."""
        pool = all_pruned_by_depth.get(depth, [])
        if not pool:
            return [], False
        best_pruned = max(pool, key=lambda n: (n.score, n.id))
        best_pruned.status = ThoughtStatus.ACTIVE
        self._log({"event": "backtrack", "node_id": best_pruned.id, "depth": depth})
        return [best_pruned.id], True

    def _pick_best(self, tree: ThoughtTree) -> ThoughtNode:
        """Return the highest-scoring TERMINAL node; promote best if none."""
        terminals = [n for n in tree.nodes.values() if n.status == ThoughtStatus.TERMINAL]
        if terminals:
            return max(terminals, key=lambda n: (n.score, n.id))
        # Fallback: promote the highest-scored node to TERMINAL
        best = max(tree.nodes.values(), key=lambda n: (n.score, n.id))
        best.status = ThoughtStatus.TERMINAL
        return best

    def _log(self, payload: dict[str, Any]) -> None:
        """Append an event to the JSONL log if configured."""
        if self._log_path is None:
            return
        event = {
            "timestamp_ns": time.time_ns(),
            "version": REASONING_SCHEMA_VERSION,
            "module": "reasoning.tot",
            "payload": payload,
        }
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
