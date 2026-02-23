"""GraphRAG retrieval algorithm (Data Plane).

GraphRetriever executes multi-hop BFS traversal over a KnowledgeGraph,
scoring each reachable FragmentNode by a blend of graph connectivity and
text coherence.

Data Plane component — no lifecycle or coordination logic.
"""

from __future__ import annotations

import re
from collections import deque
from hashlib import sha256

from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph
from thalos_prime.graph_rag.schema import GraphRetrievalResult
from thalos_prime.lob_decoder import BabelDecoder

_decoder = BabelDecoder()

# Default parameters (can be overridden at construction)
_DEFAULT_MAX_HOPS: int = 3
_DEFAULT_MIN_EDGE_WEIGHT: float = 0.1
_DEFAULT_ALPHA: float = 0.6
_DEFAULT_TOP_K: int = 10

# Same lightweight NER patterns as ingestion for query entity extraction
_CONCEPT_RE = re.compile(r"\b([a-z]{3,})\b")


def _query_entities(query: str) -> list[str]:
    """Extract lowercase word tokens from query as candidate entity names."""
    return sorted({m.group(1) for m in _CONCEPT_RE.finditer(query.lower())})


class GraphRetriever:
    """Data Plane component for multi-hop graph retrieval.

    Given a query string and a KnowledgeGraph, this retriever:
      1. Extracts query entity names.
      2. Finds seed EntityNodes by name or alias match.
      3. Performs BFS up to max_hops, collecting reachable FragmentNodes.
      4. Scores each fragment by (alpha * graph_score + (1-alpha) * text_score).
      5. Returns top_k results sorted by final_score DESC, fragment_id ASC.
    """

    def __init__(
        self,
        max_hops: int = _DEFAULT_MAX_HOPS,
        min_edge_weight: float = _DEFAULT_MIN_EDGE_WEIGHT,
        alpha: float = _DEFAULT_ALPHA,
        top_k: int = _DEFAULT_TOP_K,
    ) -> None:
        """Initialize the retriever.

        Args:
            max_hops: Maximum BFS hops from seed nodes.
            min_edge_weight: Prune edges below this weight.
            alpha: Weight for graph_score vs text_score (0=all-text, 1=all-graph).
            top_k: Maximum results to return.

        """
        self.max_hops = max_hops
        self.min_edge_weight = min_edge_weight
        self.alpha = alpha
        self.top_k = top_k

    def retrieve(
        self,
        query: str,
        graph: KnowledgeGraph,
    ) -> list[GraphRetrievalResult]:
        """Run graph retrieval for query against graph.

        Args:
            query: Natural language query string.
            graph: The KnowledgeGraph to query.

        Returns:
            Sorted list of GraphRetrievalResult (at most top_k).

        """
        if graph.node_count == 0:
            return []

        # Step 1 — seed node selection
        seed_entity_ids = self._find_seed_nodes(query, graph)
        if not seed_entity_ids:
            # Fall back: collect all fragment nodes
            return self._score_all_fragments(query, graph)

        # Step 2 — BFS traversal
        fragment_scores = self._bfs_collect(seed_entity_ids, graph)

        # Step 3 — build results
        results: list[GraphRetrievalResult] = []
        for frag_id, (graph_score, hop_dist, entity_ids) in fragment_scores.items():
            frag = graph.get_fragment(frag_id)
            if frag is None:
                continue
            text_score = _decoder.score_coherence(frag.text, query).overall_score / 100.0
            final = self.alpha * graph_score + (1.0 - self.alpha) * text_score
            results.append(
                GraphRetrievalResult(
                    fragment_id=frag_id,
                    artifact_id=frag.artifact_id,
                    text=frag.text,
                    graph_score=graph_score,
                    text_score=text_score,
                    final_score=final,
                    hop_distance=hop_dist,
                    entity_ids=sorted(entity_ids),
                )
            )

        # Step 4 — sort: final_score DESC, fragment_id ASC
        results.sort(key=lambda r: (-r.final_score, r.fragment_id))
        return results[: self.top_k]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_seed_nodes(self, query: str, graph: KnowledgeGraph) -> list[str]:
        """Find EntityNode IDs matching query tokens."""
        tokens = _query_entities(query)
        seen: set[str] = set()
        seeds: list[str] = []
        for token in tokens:
            node = graph.find_entity_by_name(token)
            if node and node.id not in seen:
                seen.add(node.id)
                seeds.append(node.id)
                continue
            for alias_node in graph.find_entity_by_alias(token):
                if alias_node.id not in seen:
                    seen.add(alias_node.id)
                    seeds.append(alias_node.id)
        return seeds

    def _bfs_collect(
        self,
        seed_ids: list[str],
        graph: KnowledgeGraph,
    ) -> dict[str, tuple[float, int, set[str]]]:
        """BFS from seed nodes; collect fragment IDs with graph scores.

        Returns:
            {fragment_id: (graph_score, hop_distance, {entity_ids})}

        """
        # queue entries: (node_id, hop_depth, accumulated_weight)
        queue: deque[tuple[str, int, float]] = deque()
        visited_nodes: set[str] = set()
        fragment_data: dict[str, tuple[float, int, set[str]]] = {}

        for sid in seed_ids:
            queue.append((sid, 0, 1.0))
            visited_nodes.add(sid)

        while queue:
            node_id, depth, acc_weight = queue.popleft()

            # Collect fragments linked to this entity
            attrs = graph._graph.nodes.get(node_id, {})
            if attrs.get("node_type") == "entity":
                for frag in graph.fragments_for_entity(node_id):
                    if frag.id not in fragment_data:
                        fragment_data[frag.id] = (0.0, depth, set())
                    old_score, old_hop, old_entities = fragment_data[frag.id]
                    fragment_data[frag.id] = (
                        max(old_score, acc_weight),
                        min(old_hop, depth),
                        old_entities | {node_id},
                    )

            if depth >= self.max_hops:
                continue

            # Expand neighbors (deterministic order via neighbors_of)
            for nbr_id, edge_attrs in graph.neighbors_of(node_id):
                weight = float(edge_attrs.get("weight", 0.0))
                if weight < self.min_edge_weight:
                    continue
                if nbr_id not in visited_nodes:
                    visited_nodes.add(nbr_id)
                    queue.append((nbr_id, depth + 1, acc_weight * weight))

        return fragment_data

    def _score_all_fragments(
        self, query: str, graph: KnowledgeGraph
    ) -> list[GraphRetrievalResult]:
        """Fallback: score all FragmentNodes by text_score alone."""
        results: list[GraphRetrievalResult] = []
        for nid, attrs in graph._graph.nodes(data=True):
            if attrs.get("node_type") != "fragment":
                continue
            frag = graph.get_fragment(str(nid))
            if frag is None:
                continue
            text_score = _decoder.score_coherence(frag.text, query).overall_score / 100.0
            results.append(
                GraphRetrievalResult(
                    fragment_id=frag.id,
                    artifact_id=frag.artifact_id,
                    text=frag.text,
                    graph_score=0.0,
                    text_score=text_score,
                    final_score=text_score,
                    hop_distance=0,
                )
            )
        results.sort(key=lambda r: (-r.final_score, r.fragment_id))
        return results[: self.top_k]

    @staticmethod
    def _result_id(query: str, fragment_id: str) -> str:
        """Stable result ID for debugging."""
        return sha256(f"{query}:{fragment_id}".encode()).hexdigest()
