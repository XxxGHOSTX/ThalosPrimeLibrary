"""Execution graph model — DAG of ExecutionNode instances."""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass

from thalos_prime.execution_ir.hash import hash_dict
from thalos_prime.execution_ir.node import ExecutionNode


@dataclass
class ExecutionGraph:
    """Directed acyclic graph of ExecutionNode instances.

    Tracks nodes, directed edges, version history, and a content-
    addressed graph hash for deterministic replay and provenance.
    """

    id: str
    nodes: dict[str, ExecutionNode]
    edges: list[tuple[str, str]]
    metadata: dict[str, object]
    parent_id: str | None
    version: int
    graph_hash: str

    def add_node(self, node: ExecutionNode) -> None:
        """Add a node to the graph.

        Args:
            node: ExecutionNode to add. Its id must be unique within this graph.

        """
        self.nodes[node.id] = node

    def add_edge(self, src: str, dst: str) -> None:
        """Add a directed edge from src node to dst node.

        Args:
            src: ID of the source node.
            dst: ID of the destination node.

        """
        self.edges.append((src, dst))

    def compute_graph_hash(self) -> None:
        """Recompute and store the graph hash from current nodes and edges.

        The hash is a deterministic function of all node dicts and edge tuples.
        Mutates self.graph_hash in-place.
        """
        nodes_data: dict[str, object] = {nid: n.to_dict() for nid, n in sorted(self.nodes.items())}
        edges_list: list[list[str]] = sorted([list(e) for e in self.edges])
        edges_data: list[object] = [list(e) for e in edges_list]
        self.graph_hash = hash_dict(
            {
                "nodes": nodes_data,
                "edges": edges_data,
                "version": self.version,
            }
        )

    def validate_dag(self) -> None:
        """Validate that the graph contains no cycles.

        Raises:
            ValueError: If a cycle is detected in the edge set.

        """
        adjacency: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for src, dst in self.edges:
            adjacency.setdefault(src, []).append(dst)

        visited: set[str] = set()
        rec_stack: set[str] = set()

        def _dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for neighbour in adjacency.get(node_id, []):
                if neighbour not in visited:
                    if _dfs(neighbour):
                        return True
                elif neighbour in rec_stack:
                    return True
            rec_stack.discard(node_id)
            return False

        for nid in list(self.nodes):
            if nid not in visited and _dfs(nid):
                msg = f"Cycle detected in execution graph '{self.id}'"
                raise ValueError(msg)

    def serialize(self) -> dict[str, object]:
        """Serialize the full graph to a JSON-safe dictionary.

        Returns:
            Dictionary representation suitable for JSON persistence.

        """
        return {
            "id": self.id,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [list(e) for e in self.edges],
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "version": self.version,
            "graph_hash": self.graph_hash,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> ExecutionGraph:
        """Deserialize a graph from a dictionary produced by serialize().

        Args:
            d: Dictionary in the format produced by serialize().

        Returns:
            Reconstructed ExecutionGraph instance.

        """
        raw_nodes = d.get("nodes", {})
        nodes: dict[str, ExecutionNode] = {}
        if isinstance(raw_nodes, dict):
            for nid, ndata in raw_nodes.items():
                if isinstance(ndata, dict):
                    nodes[nid] = ExecutionNode.from_dict(ndata)

        raw_edges = d.get("edges", [])
        edges: list[tuple[str, str]] = []
        if isinstance(raw_edges, list):
            edges.extend(
                (str(e[0]), str(e[1]))
                for e in raw_edges
                if isinstance(e, (list, tuple)) and len(e) >= 2
            )

        raw_meta = d.get("metadata", {})
        metadata: dict[str, object] = dict(raw_meta) if isinstance(raw_meta, dict) else {}

        return cls(
            id=str(d["id"]),
            nodes=nodes,
            edges=edges,
            metadata=metadata,
            parent_id=str(d["parent_id"]) if d.get("parent_id") is not None else None,
            version=int(str(d.get("version", 1))),
            graph_hash=str(d.get("graph_hash", "")),
        )

    @classmethod
    def new(
        cls,
        metadata: dict[str, object] | None = None,
        parent_id: str | None = None,
    ) -> ExecutionGraph:
        """Create a new, empty ExecutionGraph with a generated UUID.

        Args:
            metadata: Optional metadata dictionary for this graph.
            parent_id: Optional parent graph ID for lineage tracking.

        Returns:
            New ExecutionGraph with version=1 and empty nodes/edges.

        """
        graph_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.UTC).isoformat()
        graph = cls(
            id=graph_id,
            nodes={},
            edges=[],
            metadata=metadata if metadata is not None else {"created_at": now},
            parent_id=parent_id,
            version=1,
            graph_hash="",
        )
        graph.compute_graph_hash()
        return graph


__all__ = ["ExecutionGraph"]
