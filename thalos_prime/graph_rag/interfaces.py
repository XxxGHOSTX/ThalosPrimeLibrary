"""GraphRAG interfaces — typed Protocols for knowledge graph and retrieval.

All public interfaces are defined here as strict typing Protocols so that
concrete implementations (simple_graph, retriever) are interchangeable and
testable in isolation.

Design principles:
    * No concrete logic in this file — pure interface definitions only.
    * All methods carry full type annotations (Python 3.12+).
    * Lifecycle methods are part of every major interface.
    * No Any types without explicit cast and rationale comment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Data-transfer objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphNode:
    """An immutable node in the knowledge graph.

    Attributes:
        node_id:    Unique identifier for this node (e.g., entity name).
        label:      Human-readable label.
        properties: Arbitrary string-keyed metadata for this node.

    """

    node_id: str
    label: str
    properties: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    """An immutable directed, typed edge in the knowledge graph.

    Attributes:
        source_id:  node_id of the source node.
        target_id:  node_id of the target node.
        relation:   Typed relation label (e.g., "is_a", "part_of", "causes").
        weight:     Confidence / strength of this edge in [0.0, 1.0].
        properties: Arbitrary string-keyed metadata for this edge.

    """

    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    properties: dict[str, str] = field(default_factory=dict)


@dataclass
class RetrievalCandidate:
    """A single retrieval result returned by a Retriever.

    Attributes:
        content:  The retrieved text fragment or structured content.
        score:    Composite relevance score in [0.0, 1.0].
        source:   Identifier of the retrieval source (e.g., "graph", "vector").
        metadata: String-keyed metadata about this candidate.

    """

    content: str
    score: float
    source: str
    metadata: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class KnowledgeGraph(Protocol):
    """Protocol for a deterministic, traversable knowledge graph.

    Implementors must provide full lifecycle support and deterministic
    behaviour: given identical sequences of add_node / add_edge calls,
    query results must be identical.
    """

    # --- Lifecycle ---

    def initialize(self) -> None:
        """Allocate internal data structures.

        Must succeed or raise a typed exception.
        Must be idempotent: calling twice must not corrupt state.
        """
        ...

    def validate(self) -> bool:
        """Assert all graph invariants hold.

        Returns:
            True if the graph is consistent and ready for use.

        Raises:
            ValueError: If a required invariant is violated.

        """
        ...

    def operate(self) -> None:
        """Transition the graph to the operating state.

        After this call, add_node / add_edge / query_neighbors are
        valid operations.
        """
        ...

    def reconcile(self) -> None:
        """Converge graph to a consistent state.

        Must be idempotent.  Must deterministically succeed or raise.
        """
        ...

    def checkpoint(self) -> dict[str, object]:
        """Serialize current graph state for atomic restart.

        Returns:
            A version-stamped, JSON-serializable dict representing the
            complete graph state.

        """
        ...

    def terminate(self) -> None:
        """Release all resources held by this graph instance."""
        ...

    # --- Mutation ---

    def add_node(self, node: GraphNode) -> None:
        """Insert a node into the graph.

        Args:
            node: GraphNode to insert.  If a node with the same node_id
                  exists, the call is a no-op (idempotent).

        """
        ...

    def add_edge(self, edge: GraphEdge) -> None:
        """Insert a directed edge into the graph.

        Args:
            edge: GraphEdge to insert.  Source and target nodes must
                  already exist; raises KeyError otherwise.

        Raises:
            KeyError: If source_id or target_id is not in the graph.

        """
        ...

    # --- Query ---

    def query_neighbors(
        self,
        node_id: str,
        relation: str | None = None,
        max_depth: int = 1,
    ) -> list[GraphNode]:
        """Return reachable neighbor nodes from node_id.

        Args:
            node_id:   Starting node identifier.
            relation:  If provided, only follow edges with this relation label.
            max_depth: Maximum number of hops to traverse.

        Returns:
            List of reachable GraphNode instances (excluding the start node).
            Deterministic: results are sorted by node_id.

        Raises:
            KeyError: If node_id is not in the graph.

        """
        ...

    def find_path(
        self,
        source_id: str,
        target_id: str,
    ) -> list[str]:
        """Return the shortest directed path between two nodes.

        Args:
            source_id: Starting node identifier.
            target_id: Target node identifier.

        Returns:
            Ordered list of node_ids forming the shortest path, or an
            empty list if no path exists.

        """
        ...

    # --- Observable state ---

    @property
    def node_count(self) -> int:
        """Number of nodes currently in the graph."""
        ...

    @property
    def edge_count(self) -> int:
        """Number of edges currently in the graph."""
        ...


@runtime_checkable
class Retriever(Protocol):
    """Protocol for a retrieval component.

    Implementors combine one or more retrieval sources (graph, vector, …)
    and return a ranked list of RetrievalCandidate objects.
    """

    # --- Lifecycle ---

    def initialize(self) -> None:
        """Initialize retrieval resources.

        Must succeed or raise a typed exception.
        """
        ...

    def validate(self) -> bool:
        """Assert all retriever invariants hold.

        Returns:
            True if the retriever is ready to serve queries.

        Raises:
            ValueError: If a required invariant is violated.

        """
        ...

    def operate(self) -> None:
        """Transition retriever to the operating state."""
        ...

    def reconcile(self) -> None:
        """Converge retriever to a consistent state."""
        ...

    def checkpoint(self) -> dict[str, object]:
        """Serialize retriever state for restart.

        Returns:
            JSON-serializable state dict.

        """
        ...

    def terminate(self) -> None:
        """Release all resources held by this retriever."""
        ...

    # --- Query ---

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalCandidate]:
        """Retrieve the top-k most relevant candidates for query.

        Args:
            query: Natural-language or structured query string.
            top_k: Maximum number of candidates to return.

        Returns:
            List of RetrievalCandidate objects sorted by score descending.
            Length is at most top_k.

        """
        ...


__all__: list[str] = [
    "GraphEdge",
    "GraphNode",
    "KnowledgeGraph",
    "RetrievalCandidate",
    "Retriever",
]
