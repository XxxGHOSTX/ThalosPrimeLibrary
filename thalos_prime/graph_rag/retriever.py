"""Thalos Prime - Hybrid Graph Retriever.

Data Plane component that performs retrieval-augmented generation by
combining knowledge graph traversal with text-based scoring.

Data Plane boundary: computational work only — no lifecycle orchestration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from thalos_prime.graph_rag.interfaces import GraphEdge, GraphNode, GraphQueryResult
from thalos_prime.graph_rag.simple_graph import SimpleKnowledgeGraph
from thalos_prime.library_of_sense.core.interfaces import (
    RetrievalResult,
    ValidationResult,
)
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)

_TEXT_PREVIEW_LENGTH = 200


@dataclass
class HybridResult:
    """Combined graph + text retrieval result.

    Attributes:
        graph_result: Subgraph from knowledge graph traversal.
        text_matches: Text-based retrieval results.
        combined_score: Weighted combination of graph and text scores.

    """

    graph_result: GraphQueryResult
    text_matches: list[RetrievalResult] = field(default_factory=list)
    combined_score: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this result.

        """
        return {
            "graph_result": self.graph_result.to_dict(),
            "text_matches": [m.to_dict() for m in self.text_matches],
            "combined_score": self.combined_score,
        }


class HybridRetriever(BaseLifecycleComponent):
    """Hybrid retriever combining graph traversal and text matching.

    Uses a SimpleKnowledgeGraph for graph-based retrieval and supplements
    results with text-scored matches from indexed content. All operations
    are deterministic.
    """

    def __init__(
        self,
        seed: int = 0,
        graph_weight: float = 0.7,
        text_weight: float = 0.3,
    ) -> None:
        """Initialize the hybrid retriever.

        Args:
            seed: Deterministic seed for replay identification.
            graph_weight: Weight for graph-based scoring (0.0 to 1.0).
            text_weight: Weight for text-based scoring (0.0 to 1.0).

        """
        super().__init__("HybridRetriever", seed=seed)
        self._graph = SimpleKnowledgeGraph(seed=seed)
        self._graph_weight = graph_weight
        self._text_weight = text_weight
        self._indexed_texts: list[str] = []
        self._query_count: int = 0

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the hybrid retriever and its graph backend."""
        self._graph.initialize()
        self._indexed_texts = []
        self._query_count = 0
        self._initialized = True
        self._emit_event("initialize", "graph initialized, text index cleared")
        logger.debug("HybridRetriever initialized")

    def validate(self) -> ValidationResult:
        """Validate that the retriever is ready.

        Returns:
            ValidationResult indicating readiness.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="HybridRetriever not initialized; call initialize() first",
            )
        graph_validation = self._graph.validate()
        if not graph_validation.valid:
            return ValidationResult(
                valid=False,
                message=f"Graph backend invalid: {graph_validation.message}",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"HybridRetriever ready: {self._graph.node_count()} nodes, "
                f"{len(self._indexed_texts)} texts, "
                f"{self._query_count} queries"
            ),
        )

    def operate(self) -> None:
        """Log current retriever statistics. Idempotent."""
        self._emit_event(
            "operate",
            f"nodes={self._graph.node_count()} "
            f"texts={len(self._indexed_texts)} "
            f"queries={self._query_count}",
        )

    def reconcile(self) -> None:
        """Reconcile graph and text state."""
        self._graph.reconcile()
        self._query_count = max(self._query_count, 0)
        self._emit_event("reconcile", "graph reconciled, counters validated")

    def checkpoint(self) -> dict[str, object]:
        """Serialize retriever state.

        Returns:
            Dict with graph state, text index, and counters.

        """
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "graph": self._graph.checkpoint(),
            "indexed_text_count": len(self._indexed_texts),
            "query_count": self._query_count,
            "graph_weight": self._graph_weight,
            "text_weight": self._text_weight,
        }
        self._emit_event("checkpoint", f"queries={self._query_count}")
        return state

    def terminate(self) -> None:
        """Terminate retriever and release resources."""
        self._graph.terminate()
        self._indexed_texts.clear()
        self._query_count = 0
        self._initialized = False
        self._emit_event("terminate", "resources released, initialized=False")
        logger.debug("HybridRetriever terminated")

    # ------------------------------------------------------------------
    # Data Plane methods
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the underlying knowledge graph.

        Args:
            node: GraphNode to add.

        """
        self._graph.add_node(node)

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the underlying knowledge graph.

        Args:
            edge: GraphEdge to add.

        """
        self._graph.add_edge(edge)

    def index_text(self, text: str) -> None:
        """Index a text document for text-based retrieval.

        Args:
            text: Text content to index.

        """
        self._indexed_texts.append(text)
        logger.debug("Indexed text (%d chars)", len(text))

    def retrieve(self, query: str, top_k: int = 5, hops: int = 2) -> HybridResult:
        """Retrieve relevant content using graph traversal and text matching.

        Combines graph-based neighbor traversal with simple text overlap
        scoring. The combined score is a weighted sum of graph and text scores.

        Args:
            query: Query string (used as node_id for graph and keyword for text).
            top_k: Maximum number of text matches to return.
            hops: Number of graph hops for neighbor traversal.

        Returns:
            HybridResult with graph subgraph and text matches.

        """
        self._query_count += 1

        # Graph retrieval
        graph_result = self._graph.query_neighbors(query, hops=hops)

        # Text retrieval via simple keyword overlap
        text_matches: list[RetrievalResult] = []
        query_tokens = set(query.lower().split())

        for text in self._indexed_texts:
            text_tokens = set(text.lower().split())
            if not query_tokens or not text_tokens:
                continue
            overlap = len(query_tokens & text_tokens)
            if overlap > 0:
                confidence = overlap / max(len(query_tokens), 1)
                text_matches.append(
                    RetrievalResult(
                        source="text_index",
                        content=text[:_TEXT_PREVIEW_LENGTH],
                        confidence=min(confidence, 1.0),
                        metadata={"overlap_tokens": str(overlap)},
                    ),
                )

        text_matches.sort(key=lambda r: r.confidence, reverse=True)
        text_matches = text_matches[:top_k]

        # Combined scoring
        graph_score = graph_result.score
        text_score = (
            sum(m.confidence for m in text_matches) / max(len(text_matches), 1)
        )
        combined_score = (
            self._graph_weight * graph_score + self._text_weight * text_score
        )

        return HybridResult(
            graph_result=graph_result,
            text_matches=text_matches,
            combined_score=combined_score,
        )


__all__ = ["HybridResult", "HybridRetriever"]
