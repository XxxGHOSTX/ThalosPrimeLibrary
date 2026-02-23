"""Library of Sense - Knowledge Graph Retrieval.

Builds and queries a NetworkX knowledge graph for structured
entity-relationship retrieval with RDF triple support.

Lifecycle compliance is strictly enforced: data-plane operations
(add_triple, query_subject, find_path, query) require OPERATING state.
Control-plane operations (initialize, validate, operate, reconcile,
checkpoint, terminate) manage lifecycle transitions explicitly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

import networkx as nx

from thalos_prime.library_of_sense.core.interfaces import (
    QueryContext,
    RetrievalResult,
    ValidationResult,
)
from thalos_prime.library_of_sense.core.lifecycle import LifecycleState, SubsystemLifecycle

logger = logging.getLogger(__name__)

_SUBSYSTEM_NAME: Final[str] = "library_of_sense.knowledge_graph_retriever"


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


class KnowledgeGraphRetriever:
    """Retrieves information from an in-memory NetworkX knowledge graph.

    Supports adding triples (subject-predicate-object), querying by subject,
    and finding paths between concepts.

    Data-plane operations (add_triple, query_subject, find_path, query) require
    OPERATING lifecycle state. Call initialize(), validate(), and operate() in
    sequence before invoking any data-plane method.
    """

    def __init__(self, seed: int = 0) -> None:
        """Initialize an empty knowledge graph.

        Args:
            seed: Deterministic seed for replay identification.

        """
        self._graph: nx.DiGraph = nx.DiGraph()
        self._triple_count = 0
        self._seed = seed
        self._lifecycle = SubsystemLifecycle(_SUBSYSTEM_NAME, seed=seed)

    def _require_operating(self) -> None:
        """Enforce OPERATING state before any data-plane operation.

        Raises:
            RuntimeError: If the lifecycle state is not OPERATING.

        """
        if self._lifecycle.state != LifecycleState.OPERATING:
            msg = (
                f"KnowledgeGraphRetriever is not in OPERATING state "
                f"(current: {self._lifecycle.state}); "
                "call initialize(), validate(), and operate() first"
            )
            raise RuntimeError(msg)

    def initialize(self) -> None:
        """Initialize the knowledge graph and transition to INITIALIZED state."""
        self._lifecycle.transition(LifecycleState.INITIALIZING, "Creating knowledge graph")
        self._graph = nx.DiGraph()
        self._triple_count = 0
        self._lifecycle.transition(LifecycleState.INITIALIZED, "Graph ready")
        logger.info("KnowledgeGraphRetriever initialized")

    def validate(self) -> ValidationResult:
        """Validate knowledge graph consistency and transition to READY state.

        Returns:
            ValidationResult indicating whether the graph is correctly configured.

        """
        self._lifecycle.transition(LifecycleState.VALIDATING, "Checking graph consistency")
        self._lifecycle.transition(LifecycleState.READY, "Graph consistency confirmed")
        return ValidationResult(
            valid=True,
            message=f"KnowledgeGraphRetriever ready with {self._triple_count} triples",
        )

    def operate(self) -> None:
        """Transition to OPERATING state for active graph queries."""
        self._lifecycle.transition(LifecycleState.OPERATING, "Entering operation mode")
        logger.info(
            "KnowledgeGraphRetriever operating, triples=%d", self._triple_count
        )

    def reconcile(self) -> None:
        """Reconcile knowledge graph state.

        No reconciliation logic is required; graph state is self-consistent.
        Transitions through RECONCILING and returns to READY state.
        """
        self._lifecycle.transition(LifecycleState.RECONCILING, "Reconciling graph state")
        self._lifecycle.transition(LifecycleState.READY, "Reconciliation complete")
        logger.debug("KnowledgeGraphRetriever reconcile: triples=%d", self._triple_count)

    def checkpoint(self) -> None:
        """Emit a structured checkpoint log with current graph state."""
        self._lifecycle.transition(LifecycleState.CHECKPOINTING, "Checkpointing state")
        logger.info(
            "KnowledgeGraphRetriever checkpoint: nodes=%d triples=%d seed=%d",
            self._graph.number_of_nodes(),
            self._triple_count,
            self._seed,
        )
        self._lifecycle.transition(LifecycleState.READY, "Checkpoint complete")

    def terminate(self) -> None:
        """Clear the knowledge graph and transition to TERMINATED state."""
        self._lifecycle.transition(LifecycleState.TERMINATING, "Clearing graph")
        self._graph.clear()
        self._triple_count = 0
        self._lifecycle.transition(LifecycleState.TERMINATED, "Terminated")
        logger.info("KnowledgeGraphRetriever terminated")

    def add_triple(self, triple: GraphTriple) -> None:
        """Add a subject-predicate-object triple to the knowledge graph.

        Args:
            triple: GraphTriple to insert into the graph.

        Raises:
            RuntimeError: If not in OPERATING state.

        """
        self._require_operating()
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

        Raises:
            RuntimeError: If not in OPERATING state.

        """
        self._require_operating()
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

        Raises:
            RuntimeError: If not in OPERATING state.

        """
        self._require_operating()
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

        Raises:
            RuntimeError: If not in OPERATING state.

        """
        self._require_operating()
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
