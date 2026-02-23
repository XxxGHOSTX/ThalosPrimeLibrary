"""Thalos Prime - Tree of Thoughts Planner.

Control Plane component that generates a deterministic tree of candidate
reasoning paths for a given query. Randomness is seeded via random.Random(seed)
to ensure identical seeds produce identical trees (fully replayable).

Control Plane boundary: coordinates reasoning strategy only.
No data-plane retrieval or computational work belongs here.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from thalos_prime.library_of_sense.core.interfaces import ValidationResult
from thalos_prime.lifecycle import BaseLifecycleComponent


@dataclass
class ThoughtNode:
    """A single node in a Tree of Thoughts reasoning tree.

    Attributes:
        thought: The reasoning step expressed as a string.
        score: Evaluation score in [0.0, 1.0] assigned by the evaluator.
        children: Ordered list of child ThoughtNode instances.
        depth: Depth of this node within the tree (root = 0).
        seed: Deterministic seed used when generating this node's children.

    """

    thought: str
    score: float
    children: list[ThoughtNode] = field(default_factory=list)
    depth: int = 0
    seed: int = 0


class TreeOfThoughtsPlanner(BaseLifecycleComponent):
    """Control Plane planner that generates Tree of Thoughts reasoning structures.

    Uses seeded random for determinism: identical (query, seed) inputs always
    produce identical tree structures. The evaluator function scores each
    candidate thought; higher scores indicate more promising reasoning paths.
    """

    def __init__(self, component_seed: int = 0) -> None:
        """Initialize the planner with a component-level seed.

        Args:
            component_seed: Seed for the component lifecycle. Individual plan
                calls may use their own seed parameter.

        """
        super().__init__("TreeOfThoughtsPlanner", seed=component_seed)
        self._plan_count: int = 0

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize planner state."""
        self._plan_count = 0
        self._initialized = True
        self._emit_event("initialize", "plan_count=0")

    def validate(self) -> ValidationResult:
        """Validate planner configuration.

        Returns:
            ValidationResult indicating whether the planner is ready.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="TreeOfThoughtsPlanner not initialized; call initialize() first",
            )
        return ValidationResult(
            valid=True,
            message=f"TreeOfThoughtsPlanner ready, plans_generated={self._plan_count}",
        )

    def operate(self) -> None:
        """Log current planner statistics. Idempotent."""
        self._emit_event("operate", f"plan_count={self._plan_count}")

    def reconcile(self) -> None:
        """Reconcile planner state; resets plan counter if corrupted."""
        self._plan_count = max(self._plan_count, 0)
        self._emit_event("reconcile", f"plan_count={self._plan_count}")

    def checkpoint(self) -> dict[str, object]:
        """Serialize planner state.

        Returns:
            Dict with component name, seed, and plan count.

        """
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "plan_count": self._plan_count,
        }
        self._emit_event("checkpoint", f"plan_count={self._plan_count}")
        return state

    def terminate(self) -> None:
        """Reset planner state."""
        self._plan_count = 0
        self._initialized = False
        self._emit_event("terminate", "plan_count reset, initialized=False")

    # ------------------------------------------------------------------
    # Data methods
    # ------------------------------------------------------------------

    def plan(
        self,
        query: str,
        evaluator: Callable[[str], float],
        breadth: int = 3,
        depth: int = 3,
        seed: int = 42,
    ) -> ThoughtNode:
        """Generate a tree of candidate reasoning paths.

        Uses seeded random for determinism: identical (query, breadth, depth, seed)
        inputs always produce the same tree structure.

        Args:
            query: The root question or task to reason about.
            evaluator: Function that scores a thought string in [0.0, 1.0].
            breadth: Number of candidate thoughts generated per node.
            depth: Maximum depth of the reasoning tree.
            seed: Deterministic seed for this planning run.

        Returns:
            Root ThoughtNode with all children populated.

        """
        rng = random.Random(seed)  # noqa: S311  # deterministic seeded RNG, not security
        root = ThoughtNode(thought=query, score=1.0, depth=0, seed=seed)
        self._expand_node(root, evaluator, breadth, depth, rng)
        self._plan_count += 1
        self._emit_event("plan", f"query={query!r} breadth={breadth} depth={depth} seed={seed}")
        return root

    def _expand_node(
        self,
        node: ThoughtNode,
        evaluator: Callable[[str], float],
        breadth: int,
        max_depth: int,
        rng: random.Random,
    ) -> None:
        """Recursively expand a node up to max_depth.

        Args:
            node: The node to expand.
            evaluator: Thought scoring function.
            breadth: Number of children per node.
            max_depth: Maximum recursion depth.
            rng: Seeded random instance for determinism.

        """
        if node.depth >= max_depth:
            return
        child_seed_base = rng.randint(0, 2**31 - 1)
        for i in range(breadth):
            child_seed = child_seed_base + i
            child_thought = f"{node.thought} [step {node.depth + 1}.{i + 1}]"
            child_score = evaluator(child_thought)
            child = ThoughtNode(
                thought=child_thought,
                score=child_score,
                depth=node.depth + 1,
                seed=child_seed,
            )
            self._expand_node(child, evaluator, breadth, max_depth, rng)
            node.children.append(child)

    def best_path(self, root: ThoughtNode) -> list[str]:
        """Traverse the tree greedily by score to find the highest-scoring chain.

        At each node, selects the child with the highest score.

        Args:
            root: Root of the thought tree.

        Returns:
            List of thought strings from root to the greedy leaf.

        """
        path: list[str] = [root.thought]
        node = root
        while node.children:
            best_child = max(node.children, key=lambda c: c.score)
            path.append(best_child.thought)
            node = best_child
        return path

    def prune(self, root: ThoughtNode, threshold: float = 0.3) -> ThoughtNode:
        """Remove all subtrees whose score is below the confidence threshold.

        Args:
            root: Root of the thought tree to prune.
            threshold: Minimum score; nodes strictly below are removed.

        Returns:
            The root node with low-confidence subtrees removed in place.

        """
        root.children = [
            self.prune(child, threshold)
            for child in root.children
            if child.score >= threshold
        ]
        return root


__all__ = ["ThoughtNode", "TreeOfThoughtsPlanner"]
