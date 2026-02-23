"""SimpleKnowledgeGraph — deterministic, in-memory KnowledgeGraph implementation.

This module provides a concrete KnowledgeGraph backed by plain Python
dictionaries and networkx.DiGraph.  No external database is required.

Determinism guarantee:
    Given identical sequences of add_node() and add_edge() calls (and
    identical node_ids), query_neighbors() and find_path() return
    identical results on every execution.  Internal structures use sorted
    iteration where ordering matters.

Control-plane / data-plane boundary:
    SimpleKnowledgeGraph is a DATA-PLANE component.  It stores and
    traverses graph data.  Lifecycle coordination (when to call
    initialize / validate / operate / …) belongs to the caller.

State surfaces:
    node_count  — int, observable via property.
    edge_count  — int, observable via property.

Checkpoint format (v1):
    {
        "schema_version": 1,
        "node_count": <int>,
        "edge_count": <int>,
        "nodes": [{"node_id": …, "label": …, "properties": {…}}, …],
        "edges": [{"source_id": …, "target_id": …, "relation": …,
                   "weight": …, "properties": {…}}, …]
    }
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Final

import networkx as nx

from thalos_prime.graph_rag.interfaces import GraphEdge, GraphNode, RetrievalCandidate

logger = logging.getLogger(__name__)

_CHECKPOINT_SCHEMA_VERSION: Final[int] = 1


class SimpleKnowledgeGraph:
    """In-memory, deterministic knowledge graph backed by networkx.DiGraph.

    Attributes:
        _graph:     The underlying directed graph.
        _nodes:     Dict mapping node_id -> GraphNode for O(1) lookup.
        _ready:     True after initialize() and validate() succeed.
        _operating: True after operate() is called.

    """

    def __init__(self) -> None:
        """Create an empty, uninitialized graph."""
        self._graph: nx.DiGraph = nx.DiGraph()
        self._nodes: dict[str, GraphNode] = {}
        self._ready: bool = False
        self._operating: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Allocate internal data structures.

        Idempotent: calling a second time resets the graph to empty.
        Emits a structured lifecycle log event.
        """
        self._graph = nx.DiGraph()
        self._nodes = {}
        self._ready = False
        self._operating = False
        logger.info(
            '{"schema_version": 1, "event": "initialize", "component": '
            '"SimpleKnowledgeGraph", "details": {"node_count": 0, "edge_count": 0}}'
        )

    def validate(self) -> bool:
        """Assert graph invariants.

        Invariants:
            * Every edge source and target exists in _nodes.
            * _graph node count equals _nodes count.
            * Edge weights are in [0.0, 1.0].

        Returns:
            True if all invariants hold.

        Raises:
            ValueError: If any invariant is violated.

        """
        if self._graph.number_of_nodes() != len(self._nodes):
            msg = (
                f"Graph node count {self._graph.number_of_nodes()} does not "
                f"match internal node registry size {len(self._nodes)}"
            )
            raise ValueError(msg)

        for u, v, data in self._graph.edges(data=True):
            if str(u) not in self._nodes:
                msg = f"Edge source '{u}' missing from node registry"
                raise ValueError(msg)
            if str(v) not in self._nodes:
                msg = f"Edge target '{v}' missing from node registry"
                raise ValueError(msg)
            weight: float = float(data.get("weight", 1.0))
            if not (0.0 <= weight <= 1.0):
                msg = f"Edge ({u} -> {v}) has weight {weight} outside [0.0, 1.0]"
                raise ValueError(msg)

        self._ready = True
        logger.info(
            "SimpleKnowledgeGraph validate: valid=true node_count=%d edge_count=%d",
            len(self._nodes),
            self._graph.number_of_edges(),
        )
        return True

    def operate(self) -> None:
        """Transition to the operating state.

        Raises:
            RuntimeError: If validate() has not been called successfully.

        """
        if not self._ready:
            msg = "SimpleKnowledgeGraph.operate() called before validate()"
            raise RuntimeError(msg)
        self._operating = True
        logger.info(
            "SimpleKnowledgeGraph operate: node_count=%d edge_count=%d",
            len(self._nodes),
            self._graph.number_of_edges(),
        )

    def reconcile(self) -> None:
        """Converge graph to a consistent state.

        Removes any networkx nodes that are not present in _nodes
        (orphaned nodes), ensuring the two structures are in sync.
        Idempotent.
        """
        orphaned = [n for n in list(self._graph.nodes()) if str(n) not in self._nodes]
        for node_id in orphaned:
            self._graph.remove_node(node_id)
            logger.warning(
                "SimpleKnowledgeGraph reconcile: removed orphan node_id=%s",
                node_id,
            )
        logger.info(
            "SimpleKnowledgeGraph reconcile: orphans_removed=%d node_count=%d edge_count=%d",
            len(orphaned),
            len(self._nodes),
            self._graph.number_of_edges(),
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialize graph state for atomic restart.

        Returns:
            A JSON-serializable dict with schema_version, node list,
            and edge list.

        """
        nodes_snapshot: list[dict[str, object]] = [
            {
                "node_id": n.node_id,
                "label": n.label,
                "properties": dict(n.properties),
            }
            for n in sorted(self._nodes.values(), key=lambda x: x.node_id)
        ]
        edges_snapshot: list[dict[str, object]] = [
            {
                "source_id": str(u),
                "target_id": str(v),
                "relation": str(data.get("relation", "")),
                "weight": float(data.get("weight", 1.0)),
                "properties": {
                    k: str(val)
                    for k, val in data.items()
                    if k not in ("relation", "weight")
                },
            }
            for u, v, data in sorted(
                self._graph.edges(data=True),
                key=lambda e: (str(e[0]), str(e[1])),
            )
        ]
        state: dict[str, object] = {
            "schema_version": _CHECKPOINT_SCHEMA_VERSION,
            "node_count": len(self._nodes),
            "edge_count": self._graph.number_of_edges(),
            "nodes": nodes_snapshot,
            "edges": edges_snapshot,
        }
        logger.info(
            "SimpleKnowledgeGraph checkpoint: node_count=%d edge_count=%d",
            len(self._nodes),
            self._graph.number_of_edges(),
        )
        return state

    def terminate(self) -> None:
        """Release all resources and reset to uninitialized state."""
        self._graph.clear()
        self._nodes.clear()
        self._ready = False
        self._operating = False
        logger.info("SimpleKnowledgeGraph terminate")

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        """Insert a node; idempotent if node_id already present.

        Args:
            node: GraphNode to insert.

        """
        if node.node_id in self._nodes:
            return
        self._nodes[node.node_id] = node
        self._graph.add_node(node.node_id, label=node.label, **node.properties)
        logger.debug("SimpleKnowledgeGraph add_node: node_id=%s", node.node_id)

    def add_edge(self, edge: GraphEdge) -> None:
        """Insert a directed edge.

        Args:
            edge: GraphEdge to insert.

        Raises:
            KeyError: If source_id or target_id is not in the graph.

        """
        if edge.source_id not in self._nodes:
            msg = f"source node '{edge.source_id}' does not exist in graph"
            raise KeyError(msg)
        if edge.target_id not in self._nodes:
            msg = f"target node '{edge.target_id}' does not exist in graph"
            raise KeyError(msg)
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            relation=edge.relation,
            weight=edge.weight,
            **edge.properties,
        )
        logger.debug(
            "SimpleKnowledgeGraph add_edge: source=%s target=%s relation=%s",
            edge.source_id,
            edge.target_id,
            edge.relation,
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query_neighbors(
        self,
        node_id: str,
        relation: str | None = None,
        max_depth: int = 1,
    ) -> list[GraphNode]:
        """Return reachable neighbor nodes via BFS up to max_depth hops.

        Args:
            node_id:   Starting node identifier.
            relation:  If provided, only traverse edges with this label.
            max_depth: Maximum BFS depth (>= 1).

        Returns:
            Sorted list of reachable GraphNode instances (start node excluded).

        Raises:
            KeyError: If node_id is not in the graph.

        """
        if node_id not in self._nodes:
            msg = f"Node '{node_id}' not found in graph"
            raise KeyError(msg)

        visited: set[str] = {node_id}
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        result: list[GraphNode] = []

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for _, neighbor_id, data in self._graph.out_edges(current_id, data=True):
                neighbor_str = str(neighbor_id)
                if neighbor_str in visited:
                    continue
                edge_relation = str(data.get("relation", ""))
                if relation is not None and edge_relation != relation:
                    continue
                visited.add(neighbor_str)
                if neighbor_str in self._nodes:
                    result.append(self._nodes[neighbor_str])
                queue.append((neighbor_str, depth + 1))

        return sorted(result, key=lambda n: n.node_id)

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
            List of node_ids (including source and target), or empty
            list if no path exists or nodes are missing.

        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return []
        try:
            path: list[str] = nx.shortest_path(self._graph, source_id, target_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
        return path

    # ------------------------------------------------------------------
    # Retrieval helper (used by HybridRetriever)
    # ------------------------------------------------------------------

    def retrieve_context(
        self,
        node_id: str,
        max_depth: int = 2,
    ) -> list[RetrievalCandidate]:
        """Build RetrievalCandidate list from graph neighbourhood.

        Walks max_depth hops from node_id and converts each reachable
        node + its connecting edges into a RetrievalCandidate.

        Args:
            node_id:   Query entity node identifier.
            max_depth: BFS traversal depth.

        Returns:
            List of RetrievalCandidate objects, score = edge weight,
            sorted by score descending.  Empty list if node_id is unknown.

        """
        if node_id not in self._nodes:
            return []

        candidates: list[RetrievalCandidate] = []
        visited: set[str] = {node_id}
        queue: deque[tuple[str, int, float]] = deque([(node_id, 0, 1.0)])

        while queue:
            current_id, depth, cumulative_weight = queue.popleft()
            if depth >= max_depth:
                continue
            for _, neighbor_id, data in self._graph.out_edges(current_id, data=True):
                neighbor_str = str(neighbor_id)
                if neighbor_str in visited:
                    continue
                visited.add(neighbor_str)
                edge_relation = str(data.get("relation", "related_to"))
                edge_weight = float(data.get("weight", 1.0))
                hop_score = cumulative_weight * edge_weight
                neighbor_label = (
                    self._nodes[neighbor_str].label
                    if neighbor_str in self._nodes
                    else neighbor_str
                )
                content = (
                    f"{current_id} --[{edge_relation}]--> {neighbor_str} ({neighbor_label})"
                )
                candidates.append(
                    RetrievalCandidate(
                        content=content,
                        score=round(hop_score, 6),
                        source="graph",
                        metadata={
                            "source_node": current_id,
                            "target_node": neighbor_str,
                            "relation": edge_relation,
                            "depth": str(depth + 1),
                        },
                    )
                )
                queue.append((neighbor_str, depth + 1, hop_score))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    # ------------------------------------------------------------------
    # Observable state
    # ------------------------------------------------------------------

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of directed edges in the graph."""
        return int(self._graph.number_of_edges())

    @property
    def is_ready(self) -> bool:
        """True if validate() has been called successfully."""
        return self._ready


__all__: list[str] = ["SimpleKnowledgeGraph"]
