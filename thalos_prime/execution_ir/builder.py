"""GraphBuilder — constructs minimal ExecutionGraphs from generic payloads."""

from __future__ import annotations

import datetime

from thalos_prime.execution_ir.graph import ExecutionGraph
from thalos_prime.execution_ir.node import (
    ExecutionNode,
    FailureMode,
    NodeKind,
    NodeStatus,
)
from thalos_prime.execution_ir.signature import get_env_signature


class GraphBuilder:
    """Builds deterministic ExecutionGraphs from generic payload dictionaries.

    Each call to build_from_payload produces a new graph containing exactly
    one SOURCE node and one SINK node, connected by a single directed edge.
    """

    def build_from_payload(self, payload: dict[str, object]) -> ExecutionGraph:
        """Build a minimal deterministic ExecutionGraph from a generic payload.

        Creates one SOURCE node with the payload as inputs, one SINK node,
        and a SOURCE -> SINK edge.

        Args:
            payload: Arbitrary key-value data to use as the SOURCE node's inputs.

        Returns:
            A new ExecutionGraph ready for planning and execution.

        """
        graph = ExecutionGraph.new(
            metadata={"source": "GraphBuilder", "payload_keys": sorted(payload.keys())},
        )
        now = datetime.datetime.now(datetime.UTC).isoformat()
        env_sig = get_env_signature()

        source_node = ExecutionNode(
            id=f"{graph.id}:source",
            operation="source.ingest",
            kind=NodeKind.SOURCE,
            inputs=dict(payload),
            outputs={},
            dependencies=[],
            input_hash="",
            output_hash="",
            environment_signature=env_sig,
            plugin_version="1.0",
            rule_version="1.0",
            status=NodeStatus.PENDING,
            failure_mode=FailureMode.FAIL_FAST,
            created_at=now,
            started_at=None,
            finished_at=None,
            tags=["auto"],
        )
        source_node.input_hash = source_node.compute_input_hash()
        source_node.output_hash = source_node.compute_output_hash()

        sink_node = ExecutionNode(
            id=f"{graph.id}:sink",
            operation="sink.collect",
            kind=NodeKind.SINK,
            inputs={},
            outputs={},
            dependencies=[source_node.id],
            input_hash="",
            output_hash="",
            environment_signature=env_sig,
            plugin_version="1.0",
            rule_version="1.0",
            status=NodeStatus.PENDING,
            failure_mode=FailureMode.FAIL_FAST,
            created_at=now,
            started_at=None,
            finished_at=None,
            tags=["auto"],
        )
        sink_node.input_hash = sink_node.compute_input_hash()
        sink_node.output_hash = sink_node.compute_output_hash()

        graph.add_node(source_node)
        graph.add_node(sink_node)
        graph.add_edge(source_node.id, sink_node.id)
        graph.compute_graph_hash()

        return graph


__all__ = ["GraphBuilder"]
