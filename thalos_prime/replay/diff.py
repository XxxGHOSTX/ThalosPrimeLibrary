"""Graph diff utilities — compare two execution graphs node by node."""

from __future__ import annotations

from dataclasses import dataclass

from thalos_prime.execution_ir.graph import ExecutionGraph


@dataclass
class NodeDiff:
    """Records a change between two versions of a node.

    Attributes:
        node_id: ID of the node that changed.
        diff_type: One of ``"added"``, ``"removed"``, ``"hash_changed"``,
            or ``"status_changed"``.
        before: Serialized node state before the change, or None if added.
        after: Serialized node state after the change, or None if removed.

    """

    node_id: str
    diff_type: str
    before: dict[str, object] | None
    after: dict[str, object] | None


@dataclass
class GraphDiff:
    """Summary of differences between two execution graphs.

    Attributes:
        graph_id_a: ID of the first (baseline) graph.
        graph_id_b: ID of the second (comparison) graph.
        added_nodes: Node IDs present in B but not in A.
        removed_nodes: Node IDs present in A but not in B.
        changed_nodes: NodeDiff entries for nodes that exist in both graphs
            but differ in content hash or execution status.

    """

    graph_id_a: str
    graph_id_b: str
    added_nodes: list[str]
    removed_nodes: list[str]
    changed_nodes: list[NodeDiff]

    def summary(self) -> str:
        """Return a human-readable one-line diff summary.

        Returns:
            String describing counts of added, removed, and changed nodes.

        """
        return (
            f"GraphDiff({self.graph_id_a} vs {self.graph_id_b}): "
            f"+{len(self.added_nodes)} added, "
            f"-{len(self.removed_nodes)} removed, "
            f"~{len(self.changed_nodes)} changed"
        )


def diff_graphs(a: ExecutionGraph, b: ExecutionGraph) -> GraphDiff:
    """Compute the difference between two execution graphs.

    Compares node sets by ID, then checks content hashes and statuses
    for nodes that appear in both graphs.

    Args:
        a: Baseline ExecutionGraph.
        b: Comparison ExecutionGraph.

    Returns:
        GraphDiff describing added, removed, and changed nodes.

    """
    ids_a = set(a.nodes)
    ids_b = set(b.nodes)

    added = sorted(ids_b - ids_a)
    removed = sorted(ids_a - ids_b)
    changed: list[NodeDiff] = []

    for node_id in sorted(ids_a & ids_b):
        node_a = a.nodes[node_id]
        node_b = b.nodes[node_id]

        if node_a.input_hash != node_b.input_hash or node_a.output_hash != node_b.output_hash:
            changed.append(
                NodeDiff(
                    node_id=node_id,
                    diff_type="hash_changed",
                    before=node_a.to_dict(),
                    after=node_b.to_dict(),
                )
            )
        elif node_a.status != node_b.status:
            changed.append(
                NodeDiff(
                    node_id=node_id,
                    diff_type="status_changed",
                    before=node_a.to_dict(),
                    after=node_b.to_dict(),
                )
            )

    return GraphDiff(
        graph_id_a=a.id,
        graph_id_b=b.id,
        added_nodes=added,
        removed_nodes=removed,
        changed_nodes=changed,
    )


__all__ = ["GraphDiff", "NodeDiff", "diff_graphs"]
