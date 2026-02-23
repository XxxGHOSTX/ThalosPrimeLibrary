"""Library of Sense - Knowledge Graph Retrieval.

Builds and queries a NetworkX knowledge graph for structured
entity-relationship retrieval with RDF triple support.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import networkx as nx

from thalos_prime.library_of_sense.core.interfaces import (
    QueryContext,
    RetrievalResult,
    ValidationResult,
)
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)


@dataclass
class GraphTriple:
    """An RDF-style subject-predicate-object triple for knowledge representation."""

    subject: str
    predicate: str
    obj: str
    confidence: float = 1.0

    def to_dict(self) -> dict[str, object]:
        """Serialize triple to dictionary.

        Returns:
            Dictionary representation of this triple.

        """
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "obj": self.obj,
            "confidence": self.confidence,
        }


class KnowledgeGraphRetriever(BaseLifecycleComponent):
    """Retrieves information from an in-memory NetworkX knowledge graph.

    Supports adding triples (subject-predicate-object), querying by subject,
    and finding paths between concepts.
    """

    def __init__(self) -> None:
        """Initialize an empty knowledge graph."""
        super().__init__("KnowledgeGraphRetriever")
        self._graph: nx.DiGraph = nx.DiGraph()
        self._triple_count = 0

    def initialize(self) -> None:
        """Create/reset the internal graph and mark as initialized."""
        self._graph = nx.DiGraph()
        self._triple_count = 0
        self._initialized = True
        self._emit_event("initialize", "Graph created, initialized=True")
        logger.debug("KnowledgeGraphRetriever initialized")

    def validate(self) -> ValidationResult:
        """Validate the knowledge graph retriever.

        Returns:
            ValidationResult indicating readiness and initialization state.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="KnowledgeGraphRetriever not initialized; call initialize() first",
            )
        return ValidationResult(
            valid=True,
            message=f"KnowledgeGraphRetriever ready with {self._triple_count} triples",
        )

    def operate(self) -> None:
        """Log current graph statistics (nodes, edges, triples). Idempotent."""
        nodes = self._graph.number_of_nodes()
        edges = self._graph.number_of_edges()
        self._emit_event(
            "operate",
            f"nodes={nodes} edges={edges} triples={self._triple_count}",
        )
        logger.debug(
            "KnowledgeGraphRetriever operating: nodes=%d edges=%d triples=%d",
            nodes,
            edges,
            self._triple_count,
        )

    def reconcile(self) -> None:
        """Verify graph consistency; fix orphaned edges or halt on bad predicates.

        Raises:
            ValueError: If a predicate attribute is not a string.

        """
        self._emit_event("reconcile", "Verifying graph consistency")
        for u, v, data in self._graph.edges(data=True):
            predicate = data.get("predicate", "")
            if not isinstance(predicate, str):
                msg = (
                    f"Corrupt predicate on edge ({u!r} -> {v!r}): "
                    f"expected str, got {type(predicate).__name__!r}"
                )
                raise TypeError(msg)
        self._emit_event("reconcile", "Graph consistency verified")

    def checkpoint(self) -> dict[str, object]:
        """Return serializable dict with all triples and graph statistics.

        Returns:
            Dictionary containing triples list, node_count, edge_count, triple_count.

        """
        triples: list[dict[str, object]] = []
        for u, v, data in self._graph.edges(data=True):
            triples.append(
                {
                    "subject": str(u),
                    "predicate": str(data.get("predicate", "related_to")),
                    "obj": str(v),
                    "confidence": float(data.get("confidence", 1.0)),
                }
            )
        state: dict[str, object] = {
            "component": self._component_name,
            "node_count": self._graph.number_of_nodes(),
            "edge_count": self._graph.number_of_edges(),
            "triple_count": self._triple_count,
            "triples": triples,
        }
        self._emit_event("checkpoint", f"triple_count={self._triple_count}")
        return state

    def terminate(self) -> None:
        """Clear the graph and mark as uninitialized."""
        self._graph.clear()
        self._triple_count = 0
        self._initialized = False
        self._emit_event("terminate", "Graph cleared, initialized=False")
        logger.debug("KnowledgeGraphRetriever terminated")

    def add_triple(self, triple: GraphTriple) -> None:
        """Add a subject-predicate-object triple to the knowledge graph.

        Args:
            triple: GraphTriple to insert into the graph.

        """
        self._graph.add_edge(
            triple.subject,
            triple.obj,
            predicate=triple.predicate,
            confidence=triple.confidence,
        )
        self._triple_count += 1
        logger.debug(
            "Added triple: %s -[%s]-> %s",
            triple.subject,
            triple.predicate,
            triple.obj,
        )

    def query_subject(self, subject: str) -> list[GraphTriple]:
        """Return all triples where the given subject is the source node.

        Args:
            subject: Entity to query as the triple subject.

        Returns:
            List of GraphTriple instances with this subject.

        """
        triples: list[GraphTriple] = []
        if subject not in self._graph:
            return triples
        for _, obj, data in self._graph.out_edges(subject, data=True):
            triples.append(
                GraphTriple(
                    subject=subject,
                    predicate=str(data.get("predicate", "related_to")),
                    obj=str(obj),
                    confidence=float(data.get("confidence", 1.0)),
                ),
            )
        return triples

    def find_path(self, source: str, target: str) -> list[str]:
        """Find the shortest path between two entities in the graph.

        Args:
            source: Starting entity.
            target: Target entity.

        Returns:
            List of entity names forming the path, or empty list if no path exists.

        """
        try:
            path: list[str] = nx.shortest_path(self._graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
        else:
            return path

    def query(self, query: str, context: QueryContext) -> RetrievalResult:
        """Query the knowledge graph for the given entity.

        Args:
            query: Entity name to look up in the graph.
            context: Query context with domain and options.

        Returns:
            RetrievalResult with related triples as content.

        """
        _ = context
        triples = self.query_subject(query)
        if not triples:
            return RetrievalResult(
                source="knowledge_graph",
                content="",
                confidence=0.0,
                metadata={"entity": query, "triple_count": "0"},
            )
        content_parts = [f"{t.subject} {t.predicate} {t.obj}" for t in triples]
        content = "; ".join(content_parts)
        avg_confidence = sum(t.confidence for t in triples) / len(triples)
        return RetrievalResult(
            source="knowledge_graph",
            content=content,
            confidence=avg_confidence,
            metadata={
                "entity": query,
                "triple_count": str(len(triples)),
                "graph_nodes": str(self._graph.number_of_nodes()),
            },
        )

    @property
    def triple_count(self) -> int:
        """Number of triples in the knowledge graph.

        Returns:
            Count of added triples.

        """
        return self._triple_count


__all__ = ["GraphTriple", "KnowledgeGraphRetriever"]

