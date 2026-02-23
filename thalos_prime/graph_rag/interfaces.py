"""Thalos Prime - Graph-RAG Protocols and Data Types.

Defines Protocol interfaces for knowledge graph operations and
retrieval, following strict typing and deterministic contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class GraphNode:
    """A node in the knowledge graph.

    Attributes:
        node_id: Unique identifier for this node.
        label: Human-readable label or type.
        properties: Arbitrary key-value properties.

    """

    node_id: str
    label: str = ""
    properties: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize node to dictionary.

        Returns:
            Dictionary representation of this node.

        """
        return {
            "node_id": self.node_id,
            "label": self.label,
            "properties": dict(self.properties),
        }


@dataclass
class GraphEdge:
    """A directed edge in the knowledge graph.

    Attributes:
        source: Source node identifier.
        target: Target node identifier.
        relation: Relationship type or label.
        weight: Edge weight for scoring (default 1.0).

    """

    source: str
    target: str
    relation: str
    weight: float = 1.0

    def to_dict(self) -> dict[str, object]:
        """Serialize edge to dictionary.

        Returns:
            Dictionary representation of this edge.

        """
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
        }


@dataclass
class GraphQueryResult:
    """Result from a graph query operation.

    Attributes:
        nodes: Nodes matching the query.
        edges: Edges in the result subgraph.
        score: Relevance score for ranking.

    """

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    score: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this result.

        """
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "score": self.score,
        }


@runtime_checkable
class KnowledgeGraphProtocol(Protocol):
    """Protocol for knowledge graph implementations."""

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph.

        Args:
            node: Node to add.

        """
        ...

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph.

        Args:
            edge: Edge to add.

        """
        ...

    def query_neighbors(self, node_id: str, hops: int = 1) -> GraphQueryResult:
        """Query neighbors within N hops of a node.

        Args:
            node_id: Starting node identifier.
            hops: Number of hops to traverse.

        Returns:
            GraphQueryResult with discovered nodes and edges.

        """
        ...

    def node_count(self) -> int:
        """Return the total number of nodes.

        Returns:
            Number of nodes in the graph.

        """
        ...

    def edge_count(self) -> int:
        """Return the total number of edges.

        Returns:
            Number of edges in the graph.

        """
        ...


__all__ = [
    "GraphEdge",
    "GraphNode",
    "GraphQueryResult",
    "KnowledgeGraphProtocol",
]
