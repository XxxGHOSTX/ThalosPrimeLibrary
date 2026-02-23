"""Thalos Prime - Simple In-Memory Knowledge Graph.

Data Plane component providing a lightweight, deterministic knowledge graph
backed by adjacency lists. Supports node/edge management and N-hop neighbor
traversal without external dependencies.

Data Plane boundary: computational work only — no lifecycle orchestration.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from thalos_prime.graph_rag.interfaces import (
    GraphEdge,
    GraphNode,
    GraphQueryResult,
)
from thalos_prime.library_of_sense.core.interfaces import ValidationResult
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)


class SimpleKnowledgeGraph(BaseLifecycleComponent):
    """A simple in-memory knowledge graph using adjacency lists.

    Deterministic: identical operations in identical order produce identical
    internal state. No external I/O or randomness.
    """

    def __init__(self, seed: int = 0) -> None:
        """Initialize the simple knowledge graph.

        Args:
            seed: Deterministic seed for replay identification.

        """
        super().__init__("SimpleKnowledgeGraph", seed=seed)
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._adjacency: dict[str, list[GraphEdge]] = defaultdict(list)

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the graph, clearing all data."""
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._initialized = True
        self._emit_event("initialize", "graph cleared, initialized=True")
        logger.debug("SimpleKnowledgeGraph initialized")

    def validate(self) -> ValidationResult:
        """Validate that the graph is initialized.

        Returns:
            ValidationResult indicating readiness.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="SimpleKnowledgeGraph not initialized; call initialize() first",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"SimpleKnowledgeGraph ready: {len(self._nodes)} nodes, "
                f"{len(self._edges)} edges"
            ),
        )

    def operate(self) -> None:
        """Log current graph statistics. Idempotent."""
        self._emit_event(
            "operate",
            f"nodes={len(self._nodes)} edges={len(self._edges)}",
        )

    def reconcile(self) -> None:
        """Reconcile graph state by pruning edges referencing missing nodes."""
        valid_edges: list[GraphEdge] = []
        for edge in self._edges:
            if edge.source in self._nodes and edge.target in self._nodes:
                valid_edges.append(edge)
            else:
                logger.debug(
                    "Pruning dangling edge: %s -> %s",
                    edge.source,
                    edge.target,
                )
        self._edges = valid_edges
        self._adjacency.clear()
        for edge in self._edges:
            self._adjacency[edge.source].append(edge)
        self._emit_event(
            "reconcile",
            f"edges after pruning={len(self._edges)}",
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialize graph state.

        Returns:
            Dict with node and edge data for restoration.

        """
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
        }
        self._emit_event("checkpoint", f"nodes={len(self._nodes)}")
        return state

    def terminate(self) -> None:
        """Clear all graph data and reset state."""
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._initialized = False
        self._emit_event("terminate", "graph cleared, initialized=False")
        logger.debug("SimpleKnowledgeGraph terminated")

    # ------------------------------------------------------------------
    # Data Plane methods
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph.

        If a node with the same node_id already exists, it is replaced.

        Args:
            node: GraphNode to add.

        """
        self._nodes[node.node_id] = node
        logger.debug("Added node: %s", node.node_id)

    def add_edge(self, edge: GraphEdge) -> None:
        """Add a directed edge to the graph.

        Implicitly creates source and target nodes if they do not exist.

        Args:
            edge: GraphEdge to add.

        """
        if edge.source not in self._nodes:
            self._nodes[edge.source] = GraphNode(node_id=edge.source)
        if edge.target not in self._nodes:
            self._nodes[edge.target] = GraphNode(node_id=edge.target)
        self._edges.append(edge)
        self._adjacency[edge.source].append(edge)
        logger.debug("Added edge: %s -[%s]-> %s", edge.source, edge.relation, edge.target)

    def query_neighbors(self, node_id: str, hops: int = 1) -> GraphQueryResult:
        """Query neighbors within N hops of a node.

        Performs a breadth-first traversal from the given node, collecting
        all nodes and edges within the specified hop radius.

        Args:
            node_id: Starting node identifier.
            hops: Number of hops to traverse (must be >= 1).

        Returns:
            GraphQueryResult with discovered nodes and edges.

        """
        visited: set[str] = set()
        frontier: list[str] = [node_id]
        result_nodes: list[GraphNode] = []
        result_edges: list[GraphEdge] = []
        total_weight: float = 0.0

        for _ in range(hops):
            next_frontier: list[str] = []
            for current in frontier:
                if current in visited:
                    continue
                visited.add(current)
                if current in self._nodes:
                    result_nodes.append(self._nodes[current])
                for edge in self._adjacency.get(current, []):
                    result_edges.append(edge)
                    total_weight += edge.weight
                    if edge.target not in visited:
                        next_frontier.append(edge.target)
            frontier = next_frontier

        # Include final frontier nodes not yet visited
        for node in frontier:
            if node not in visited and node in self._nodes:
                visited.add(node)
                result_nodes.append(self._nodes[node])

        score = total_weight / max(len(result_edges), 1)

        return GraphQueryResult(
            nodes=result_nodes,
            edges=result_edges,
            score=score,
        )

    def node_count(self) -> int:
        """Return the total number of nodes.

        Returns:
            Number of nodes in the graph.

        """
        return len(self._nodes)

    def edge_count(self) -> int:
        """Return the total number of edges.

        Returns:
            Number of edges in the graph.

        """
        return len(self._edges)


__all__ = ["SimpleKnowledgeGraph"]
