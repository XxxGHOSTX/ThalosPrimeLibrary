"""Replay engine — deterministic re-execution of execution graphs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from thalos_prime.execution_ir.executor import DeterministicExecutor
from thalos_prime.execution_ir.node import NodeStatus
from thalos_prime.execution_ir.planner import ExecutionPlanner

if TYPE_CHECKING:
    from thalos_prime.provenance.index import ProvenanceIndex
    from thalos_prime.storage.event_log import EventLog

from thalos_prime.execution_ir.graph import ExecutionGraph


class ReplayEngine:
    """Re-executes a stored execution graph from scratch.

    Resets all node statuses to PENDING, re-plans, and re-executes.
    Optionally logs replay events and records provenance.
    """

    def __init__(
        self,
        executor: DeterministicExecutor,
        event_log: EventLog | None = None,
        provenance_index: ProvenanceIndex | None = None,
    ) -> None:
        """Initialize the replay engine.

        Args:
            executor: DeterministicExecutor used to re-execute nodes.
            event_log: Optional EventLog for logging replay start/end events.
            provenance_index: Optional ProvenanceIndex for recording node provenance.

        """
        self._executor = executor
        self._event_log = event_log
        self._provenance_index = provenance_index
        self._planner = ExecutionPlanner()

    def replay(self, graph: ExecutionGraph) -> ExecutionGraph:
        """Re-execute all nodes in the graph in topological order.

        Resets all node statuses to PENDING, re-executes using the planner
        order, recomputes hashes, and logs replay_started/replay_finished
        events. Records node provenance if a ProvenanceIndex is configured.

        Args:
            graph: ExecutionGraph to replay.

        Returns:
            Updated ExecutionGraph with re-executed node statuses and outputs.

        """
        if self._event_log is not None:
            self._event_log.log(
                "replay_started",
                graph.id,
                graph.version,
                node_count=len(graph.nodes),
            )

        for node in graph.nodes.values():
            node.status = NodeStatus.PENDING
            node.outputs = {}
            node.output_hash = node.compute_output_hash()
            node.started_at = None
            node.finished_at = None
            node.error = None

        plan = self._planner.plan(graph)
        graph = self._executor.execute_graph(graph, plan)

        if self._provenance_index is not None:
            for node in graph.nodes.values():
                self._provenance_index.record_node(graph.id, node)

        if self._event_log is not None:
            self._event_log.log(
                "replay_finished",
                graph.id,
                graph.version,
                graph_hash=graph.graph_hash,
            )

        return graph


__all__ = ["ReplayEngine"]
