"""HybridRetriever — graph traversal + vector-similarity hybrid retrieval.

This module implements the Retriever Protocol by combining:
    1. Graph retrieval  — walks the KnowledgeGraph neighbourhood of the
                          query entity (deterministic, fully implemented).
    2. Vector retrieval — nearest-neighbour similarity search over
                          document embeddings (STUB — not yet connected
                          to a vector DB; returns deterministic empty list).

The stub guarantees that Phase 1 is fully testable and deterministic
without any external service dependency.  Phase 2 will replace the stub
with a real embedding + vector-index backend.

Control-plane / data-plane boundary:
    HybridRetriever is a DATA-PLANE component.  It executes retrieval
    work only; lifecycle coordination belongs to the caller.

Determinism guarantee:
    For identical inputs (query, top_k) and identical graph state,
    retrieve() returns identical results in identical order.

State surfaces:
    is_ready      — bool, True after initialize() + validate().
    graph         — the KnowledgeGraph instance (observable externally).
    query_count   — int, monotonically increasing call counter.

Checkpoint format (v1):
    {
        "schema_version": 1,
        "query_count": <int>,
        "graph_checkpoint": { <SimpleKnowledgeGraph checkpoint> }
    }

Event log schema (v1):
    {
        "schema_version": 1,
        "event":   "retrieve",
        "ts":      "<ISO-8601 UTC>",
        "details": {"query": "…", "top_k": <int>,
                    "graph_hits": <int>, "vector_hits": <int>,
                    "total_returned": <int>}
    }
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

from thalos_prime.graph_rag.interfaces import GraphEdge, GraphNode, RetrievalCandidate

if TYPE_CHECKING:
    from thalos_prime.graph_rag.simple_graph import SimpleKnowledgeGraph

logger = logging.getLogger(__name__)

_CHECKPOINT_SCHEMA_VERSION: Final[int] = 1


class HybridRetriever:
    """Combines graph traversal with (stubbed) vector-similarity retrieval.

    Attributes:
        _graph:       The backing KnowledgeGraph.
        _ready:       True after initialize() + validate() complete.
        _operating:   True after operate() is called.
        _query_count: Monotonically increasing call counter.

    """

    def __init__(self, graph: SimpleKnowledgeGraph) -> None:
        """Initialize with a pre-constructed KnowledgeGraph.

        Args:
            graph: The SimpleKnowledgeGraph to traverse during retrieval.
                   Caller is responsible for initialising the graph.

        """
        self._graph: SimpleKnowledgeGraph = graph
        self._ready: bool = False
        self._operating: bool = False
        self._query_count: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the retriever.

        Delegates graph initialisation to the graph instance.
        Resets the query counter.
        """
        self._graph.initialize()
        self._query_count = 0
        self._ready = False
        self._operating = False
        logger.info("HybridRetriever initialize: query_count=0")

    def validate(self) -> bool:
        """Assert retriever invariants.

        Delegates graph validation to the graph instance.

        Returns:
            True if the graph validates successfully.

        Raises:
            ValueError: If graph validation fails.

        """
        graph_valid = self._graph.validate()
        if not graph_valid:
            msg = "HybridRetriever: underlying graph failed validation"
            raise ValueError(msg)
        self._ready = True
        logger.info("HybridRetriever validate: valid=true")
        return True

    def operate(self) -> None:
        """Transition to the operating state.

        Raises:
            RuntimeError: If validate() has not been called successfully.

        """
        if not self._ready:
            msg = "HybridRetriever.operate() called before validate()"
            raise RuntimeError(msg)
        self._graph.operate()
        self._operating = True
        logger.info("HybridRetriever operate: query_count=%d", self._query_count)

    def reconcile(self) -> None:
        """Converge retriever to consistent state.

        Delegates to graph reconcile.
        """
        self._graph.reconcile()
        logger.info("HybridRetriever reconcile: query_count=%d", self._query_count)

    def checkpoint(self) -> dict[str, object]:
        """Serialize retriever state.

        Returns:
            JSON-serializable dict including graph checkpoint and query_count.

        """
        state: dict[str, object] = {
            "schema_version": _CHECKPOINT_SCHEMA_VERSION,
            "query_count": self._query_count,
            "graph_checkpoint": self._graph.checkpoint(),
        }
        logger.info("HybridRetriever checkpoint: query_count=%d", self._query_count)
        return state

    def terminate(self) -> None:
        """Release all resources."""
        self._graph.terminate()
        self._ready = False
        self._operating = False
        logger.info("HybridRetriever terminate: total_queries=%d", self._query_count)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalCandidate]:
        """Retrieve top-k candidates by combining graph and vector search.

        Phase 1 behaviour:
            * Graph retrieval: walks the graph neighbourhood of the
              query (treated as a node_id).  Returns real results.
            * Vector retrieval: stub — returns empty list until a
              vector backend is wired in Phase 2.

        Candidates from both sources are merged, deduplicated by
        content, and re-ranked by score descending before top_k is applied.

        Args:
            query: Entity name / query string.  Used as node_id for
                   graph lookup and as embedding seed for vector search.
            top_k: Maximum number of candidates to return (>= 1).

        Returns:
            List of RetrievalCandidate objects, sorted by score
            descending, length <= top_k.

        Raises:
            ValueError: If top_k < 1.

        """
        if top_k < 1:
            msg = f"top_k must be >= 1, got {top_k}"
            raise ValueError(msg)

        graph_candidates = self._graph_retrieve(query)
        vector_candidates = self._vector_retrieve_stub(query)

        # Merge and deduplicate by content
        seen_content: set[str] = set()
        merged: list[RetrievalCandidate] = []
        for candidate in graph_candidates + vector_candidates:
            if candidate.content not in seen_content:
                seen_content.add(candidate.content)
                merged.append(candidate)

        merged.sort(key=lambda c: c.score, reverse=True)
        result = merged[:top_k]

        ts = datetime.now(UTC).isoformat()
        self._query_count += 1
        logger.info(
            "HybridRetriever retrieve: ts=%s query=%s top_k=%d "
            "graph_hits=%d vector_hits=%d total_returned=%d",
            ts,
            query,
            top_k,
            len(graph_candidates),
            len(vector_candidates),
            len(result),
        )
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _graph_retrieve(self, query: str) -> list[RetrievalCandidate]:
        """Retrieve candidates from the knowledge graph.

        Treats query as a node_id and walks the graph neighbourhood.
        Returns empty list if the node does not exist (not an error in Phase 1).

        Args:
            query: Node identifier to look up.

        Returns:
            List of RetrievalCandidate objects from graph traversal.

        """
        return self._graph.retrieve_context(node_id=query, max_depth=2)

    def _vector_retrieve_stub(self, _query: str) -> list[RetrievalCandidate]:
        """Deterministic stub for vector-similarity search.

        Phase 2 will replace this with a real embedding + index lookup.
        The stub is deterministic: it always returns an empty list so
        that Phase 1 tests are fully reproducible without any external service.

        Args:
            _query: Intentionally unused.  Phase 2 will use this as the
                    embedding input.

        Returns:
            Empty list.

        """
        return []

    # ------------------------------------------------------------------
    # Observable state
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """True after initialize() + validate() complete."""
        return self._ready

    @property
    def graph(self) -> SimpleKnowledgeGraph:
        """The backing KnowledgeGraph instance."""
        return self._graph

    @property
    def query_count(self) -> int:
        """Total number of retrieve() calls since last initialize()."""
        return self._query_count

    # ------------------------------------------------------------------
    # Convenience: populate graph directly
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        """Delegate add_node to the backing graph.

        Args:
            node: GraphNode to insert.

        """
        self._graph.add_node(node)

    def add_edge_to_graph(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        weight: float = 1.0,
    ) -> None:
        """Convenience wrapper to add an edge to the backing graph.

        Args:
            source_id: Source node identifier.
            target_id: Target node identifier.
            relation:  Typed relation label.
            weight:    Edge confidence in [0.0, 1.0].

        """
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
        )
        self._graph.add_edge(edge)


__all__: list[str] = ["HybridRetriever"]
