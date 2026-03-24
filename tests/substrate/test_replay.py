"""Tests for replay engine and graph diff utilities."""

from __future__ import annotations

import tempfile
from pathlib import Path

from thalos_prime.execution_ir.builder import GraphBuilder
from thalos_prime.execution_ir.executor import DeterministicExecutor
from thalos_prime.execution_ir.node import NodeStatus
from thalos_prime.execution_ir.planner import ExecutionPlanner
from thalos_prime.replay.diff import GraphDiff, NodeDiff, diff_graphs
from thalos_prime.replay.engine import ReplayEngine
from thalos_prime.storage.event_log import EventLog


class TestReplayEngine:
    """Tests for ReplayEngine deterministic re-execution."""

    def test_replay_produces_same_output_hash(self) -> None:
        """Replaying a graph produces the same output hashes as original execution."""
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 42})

        executor = DeterministicExecutor()
        planner = ExecutionPlanner()
        plan = planner.plan(graph)
        original = executor.execute_graph(graph, plan)

        original_hashes = {nid: n.output_hash for nid, n in original.nodes.items()}

        replay_engine = ReplayEngine(DeterministicExecutor())
        replayed = replay_engine.replay(original)

        for nid, orig_hash in original_hashes.items():
            assert replayed.nodes[nid].output_hash == orig_hash

    def test_replay_resets_statuses_before_execution(self) -> None:
        """ReplayEngine resets all node statuses to PENDING before re-running."""
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})

        executor = DeterministicExecutor()
        planner = ExecutionPlanner()
        plan = planner.plan(graph)
        graph = executor.execute_graph(graph, plan)

        for node in graph.nodes.values():
            assert node.status == NodeStatus.SUCCEEDED

        # Capture the succeeded states and replay
        replay_engine = ReplayEngine(DeterministicExecutor())
        replayed = replay_engine.replay(graph)

        for node in replayed.nodes.values():
            assert node.status == NodeStatus.SUCCEEDED

    def test_replay_logs_events_when_event_log_provided(self) -> None:
        """Replay logs replay_started and replay_finished events when EventLog given."""
        with tempfile.TemporaryDirectory() as tmp:
            event_log = EventLog(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"x": 1})

            executor = DeterministicExecutor()
            planner = ExecutionPlanner()
            plan = planner.plan(graph)
            graph = executor.execute_graph(graph, plan)

            replay_engine = ReplayEngine(DeterministicExecutor(), event_log=event_log)
            replay_engine.replay(graph)

            events = event_log.get_events(graph.id)
            event_types = [e.event_type for e in events]
            assert "replay_started" in event_types
            assert "replay_finished" in event_types

    def test_replay_records_provenance_when_index_provided(self) -> None:
        """Replay records node provenance when ProvenanceIndex is given."""
        with tempfile.TemporaryDirectory() as tmp:
            from thalos_prime.provenance.index import ProvenanceIndex
            prov_index = ProvenanceIndex(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"x": 1})

            executor = DeterministicExecutor()
            planner = ExecutionPlanner()
            plan = planner.plan(graph)
            graph = executor.execute_graph(graph, plan)

            replay_engine = ReplayEngine(
                DeterministicExecutor(),
                provenance_index=prov_index,
            )
            replayed = replay_engine.replay(graph)

            records = prov_index.get_by_graph(replayed.id)
            assert len(records) == len(replayed.nodes)


class TestGraphDiff:
    """Tests for graph diff utilities."""

    def test_diff_identical_graphs_no_changes(self) -> None:
        """Diffing a graph against itself returns no changes."""
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})

        diff = diff_graphs(graph, graph)
        assert diff.added_nodes == []
        assert diff.removed_nodes == []
        assert diff.changed_nodes == []

    def test_diff_detects_added_node(self) -> None:
        """diff_graphs detects nodes present in B but not in A."""
        from thalos_prime.execution_ir.node import ExecutionNode, FailureMode, NodeKind
        from thalos_prime.execution_ir.signature import get_env_signature

        builder = GraphBuilder()
        g1 = builder.build_from_payload({"x": 1})
        g2 = builder.build_from_payload({"x": 1})

        # Add an extra node to g2
        extra = ExecutionNode(
            id="extra_node",
            operation="test",
            kind=NodeKind.TRANSFORM,
            inputs={},
            outputs={},
            dependencies=[],
            input_hash="",
            output_hash="",
            environment_signature=get_env_signature(),
            plugin_version="1.0",
            rule_version="1.0",
            status=NodeStatus.PENDING,
            failure_mode=FailureMode.FAIL_FAST,
            created_at="",
            started_at=None,
            finished_at=None,
        )
        g2.add_node(extra)

        diff = diff_graphs(g1, g2)
        assert "extra_node" in diff.added_nodes

    def test_diff_detects_removed_node(self) -> None:
        """diff_graphs detects nodes present in A but not in B."""
        from thalos_prime.execution_ir.node import ExecutionNode, FailureMode, NodeKind
        from thalos_prime.execution_ir.signature import get_env_signature

        builder = GraphBuilder()
        g1 = builder.build_from_payload({"x": 1})
        g2 = builder.build_from_payload({"x": 1})

        extra = ExecutionNode(
            id="extra_node",
            operation="test",
            kind=NodeKind.TRANSFORM,
            inputs={},
            outputs={},
            dependencies=[],
            input_hash="",
            output_hash="",
            environment_signature=get_env_signature(),
            plugin_version="1.0",
            rule_version="1.0",
            status=NodeStatus.PENDING,
            failure_mode=FailureMode.FAIL_FAST,
            created_at="",
            started_at=None,
            finished_at=None,
        )
        g1.add_node(extra)

        diff = diff_graphs(g1, g2)
        assert "extra_node" in diff.removed_nodes

    def test_diff_detects_hash_changed(self) -> None:
        """diff_graphs detects nodes with changed output hashes."""
        builder = GraphBuilder()
        g1 = builder.build_from_payload({"x": 1})

        executor = DeterministicExecutor()
        planner = ExecutionPlanner()
        plan = planner.plan(g1)
        g1 = executor.execute_graph(g1, plan)

        import copy
        g2_nodes = {nid: copy.deepcopy(n) for nid, n in g1.nodes.items()}
        from thalos_prime.execution_ir.graph import ExecutionGraph
        g2 = ExecutionGraph(
            id=g1.id,
            nodes=g2_nodes,
            edges=list(g1.edges),
            metadata=dict(g1.metadata),
            parent_id=g1.parent_id,
            version=g1.version,
            graph_hash=g1.graph_hash,
        )
        # Modify an output to create a hash difference
        first_node_id = next(iter(g2.nodes))
        g2.nodes[first_node_id].outputs = {"modified": True}
        g2.nodes[first_node_id].output_hash = g2.nodes[first_node_id].compute_output_hash()

        diff = diff_graphs(g1, g2)
        changed_ids = [c.node_id for c in diff.changed_nodes]
        assert first_node_id in changed_ids

    def test_graph_diff_summary_string(self) -> None:
        """summary() returns a human-readable string."""
        diff = GraphDiff(
            graph_id_a="a",
            graph_id_b="b",
            added_nodes=["n1"],
            removed_nodes=[],
            changed_nodes=[
                NodeDiff(node_id="n2", diff_type="hash_changed", before=None, after=None)
            ],
        )
        summary = diff.summary()
        assert "a" in summary
        assert "b" in summary
        assert "+1" in summary
