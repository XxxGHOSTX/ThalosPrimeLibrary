"""Deterministic executor for execution graph nodes."""

from __future__ import annotations

import datetime
from typing import Protocol, runtime_checkable

from thalos_prime.execution_ir.graph import ExecutionGraph
from thalos_prime.execution_ir.node import ExecutionNode, NodeStatus


@runtime_checkable
class NodeOperator(Protocol):
    """Protocol for node operation handlers.

    Implementations must be callable with a node and its resolved inputs,
    returning a dictionary of output values.
    """

    def execute(
        self,
        node: ExecutionNode,
        inputs: dict[str, object],
    ) -> dict[str, object]:
        """Execute the node operation and return output values.

        Args:
            node: The ExecutionNode being executed.
            inputs: Resolved input values for the operation.

        Returns:
            Dictionary of output values produced by the operation.

        """
        ...


class DeterministicExecutor:
    """Executes ExecutionGraph nodes deterministically in a given plan order.

    Handlers are registered per operation name. Nodes without a registered
    handler execute with their inputs echoed verbatim as outputs (status
    SUCCEEDED).  This ensures input values flow through to downstream nodes
    even when no explicit handler is wired.
    """

    def __init__(self) -> None:
        """Initialize an executor with an empty handler registry."""
        self._handlers: dict[str, NodeOperator] = {}

    def register_handler(self, operation: str, handler: NodeOperator) -> None:
        """Register a NodeOperator for a specific operation name.

        Args:
            operation: Operation identifier string (e.g. "transform.normalize").
            handler: Object implementing the NodeOperator protocol.

        """
        self._handlers[operation] = handler

    def execute_node(self, node: ExecutionNode) -> ExecutionNode:
        """Execute a single node and return the updated node.

        Updates node.outputs, node.status, node.output_hash,
        node.started_at, and node.finished_at.

        If no handler is registered for the node's operation, the node
        is marked SUCCEEDED and its inputs are echoed verbatim as outputs.
        This preserves input values for downstream nodes that depend on
        this node's outputs, instead of silently swallowing them.

        Args:
            node: ExecutionNode to execute.

        Returns:
            Updated ExecutionNode with execution results applied.

        """
        node.status = NodeStatus.RUNNING
        node.started_at = datetime.datetime.now(datetime.UTC).isoformat()
        try:
            handler = self._handlers.get(node.operation)
            outputs = (
                handler.execute(node, node.inputs)
                if handler is not None
                else dict(node.inputs)
            )
            node.outputs = outputs
            node.output_hash = node.compute_output_hash()
            node.status = NodeStatus.SUCCEEDED
        except Exception as exc:
            node.status = NodeStatus.FAILED
            node.error = str(exc)
            raise
        finally:
            node.finished_at = datetime.datetime.now(datetime.UTC).isoformat()
        return node

    def execute_graph(
        self,
        graph: ExecutionGraph,
        plan: list[str],
    ) -> ExecutionGraph:
        """Execute all nodes in plan order, updating the graph in place.

        Nodes are executed sequentially in the provided plan order.
        Each executed node is updated back into graph.nodes.
        After all nodes are executed, the graph hash is recomputed.

        Args:
            graph: ExecutionGraph whose nodes will be executed.
            plan: Ordered list of node IDs to execute.

        Returns:
            The mutated ExecutionGraph with updated node statuses and outputs.

        """
        for node_id in plan:
            node = graph.nodes[node_id]
            graph.nodes[node_id] = self.execute_node(node)
        graph.compute_graph_hash()
        return graph


__all__ = ["DeterministicExecutor", "NodeOperator"]
