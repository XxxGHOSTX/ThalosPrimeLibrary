"""Provenance graph — tracks parent-child relationships between execution nodes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProvenanceEdge:
    """Represents a directed dependency between two execution nodes.

    Attributes:
        parent_node_id: ID of the upstream (producer) node.
        child_node_id: ID of the downstream (consumer) node.
        graph_id: ID of the graph containing both nodes.

    """

    parent_node_id: str
    child_node_id: str
    graph_id: str


class ProvenanceGraph:
    """In-memory graph of provenance edges between execution nodes.

    Tracks parent-child relationships independently of the execution graph
    edges, allowing cross-graph provenance queries.
    """

    def __init__(self) -> None:
        """Initialize an empty provenance graph."""
        self._edges: list[ProvenanceEdge] = []
        self._parents: dict[str, list[str]] = {}
        self._children: dict[str, list[str]] = {}

    def add_edge(self, edge: ProvenanceEdge) -> None:
        """Add a provenance edge to the graph.

        Args:
            edge: ProvenanceEdge to record.

        """
        self._edges.append(edge)
        self._children.setdefault(edge.parent_node_id, []).append(edge.child_node_id)
        self._parents.setdefault(edge.child_node_id, []).append(edge.parent_node_id)

    def get_parents(self, node_id: str) -> list[str]:
        """Return the parent node IDs for the given node.

        Args:
            node_id: Node ID to look up.

        Returns:
            List of parent node IDs (nodes this node depends on).

        """
        return list(self._parents.get(node_id, []))

    def get_children(self, node_id: str) -> list[str]:
        """Return the child node IDs for the given node.

        Args:
            node_id: Node ID to look up.

        Returns:
            List of child node IDs (nodes that depend on this node).

        """
        return list(self._children.get(node_id, []))

    def to_dict(self) -> dict[str, object]:
        """Serialize this provenance graph to a JSON-safe dictionary.

        Returns:
            Dictionary containing all edges as a list of dicts.

        """
        return {
            "edges": [
                {
                    "parent_node_id": e.parent_node_id,
                    "child_node_id": e.child_node_id,
                    "graph_id": e.graph_id,
                }
                for e in self._edges
            ]
        }


__all__ = ["ProvenanceEdge", "ProvenanceGraph"]
