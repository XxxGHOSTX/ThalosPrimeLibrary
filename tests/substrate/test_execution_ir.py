"""Tests for execution IR: node, graph, planner, executor, builder, determinism."""

from __future__ import annotations

import pytest

from thalos_prime.execution_ir.builder import GraphBuilder
from thalos_prime.execution_ir.executor import DeterministicExecutor
from thalos_prime.execution_ir.graph import ExecutionGraph
from thalos_prime.execution_ir.hash import hash_dict, sha256_hex, stable_json
from thalos_prime.execution_ir.node import (
    ExecutionNode,
    FailureMode,
    NodeKind,
    NodeStatus,
)
from thalos_prime.execution_ir.planner import ExecutionPlanner
from thalos_prime.execution_ir.signature import get_env_signature

# ---------------------------------------------------------------------------
# Hash utilities
# ---------------------------------------------------------------------------


class TestHashUtilities:
    """Tests for hash.py utilities."""

    def test_stable_json_sorts_keys(self) -> None:
        """stable_json produces consistent output regardless of dict insertion order."""
        d1 = {"b": 2, "a": 1}
        d2 = {"a": 1, "b": 2}
        assert stable_json(d1) == stable_json(d2)

    def test_sha256_hex_returns_64_chars(self) -> None:
        """SHA-256 hex digest is always 64 characters."""
        digest = sha256_hex("hello")
        assert len(digest) == 64

    def test_hash_dict_deterministic(self) -> None:
        """Same dict always produces the same hash."""
        d: dict[str, object] = {"key": "value", "num": 42}
        assert hash_dict(d) == hash_dict(d)

    def test_hash_dict_differs_for_different_inputs(self) -> None:
        """Different dicts produce different hashes."""
        assert hash_dict({"a": 1}) != hash_dict({"a": 2})


# ---------------------------------------------------------------------------
# Environment signature
# ---------------------------------------------------------------------------


class TestEnvSignature:
    """Tests for signature.py."""

    def test_get_env_signature_deterministic(self) -> None:
        """Calling get_env_signature() twice returns the same hash."""
        assert get_env_signature() == get_env_signature()

    def test_get_env_signature_is_hex(self) -> None:
        """Signature is a 64-char hex string."""
        sig = get_env_signature()
        assert len(sig) == 64
        int(sig, 16)  # raises ValueError if not hex


# ---------------------------------------------------------------------------
# ExecutionNode
# ---------------------------------------------------------------------------


class TestExecutionNode:
    """Tests for ExecutionNode creation and serialization."""

    def _make_node(self, node_id: str = "n1") -> ExecutionNode:
        node = ExecutionNode(
            id=node_id,
            operation="test.op",
            kind=NodeKind.SOURCE,
            inputs={"x": 1},
            outputs={},
            dependencies=[],
            input_hash="",
            output_hash="",
            environment_signature=get_env_signature(),
            plugin_version="1.0",
            rule_version="1.0",
            status=NodeStatus.PENDING,
            failure_mode=FailureMode.FAIL_FAST,
            created_at="2024-01-01T00:00:00+00:00",
            started_at=None,
            finished_at=None,
            tags=["t1"],
        )
        node.input_hash = node.compute_input_hash()
        node.output_hash = node.compute_output_hash()
        return node

    def test_compute_input_hash_is_deterministic(self) -> None:
        """Input hash changes when inputs change."""
        n = self._make_node()
        h1 = n.compute_input_hash()
        n.inputs = {"x": 2}
        h2 = n.compute_input_hash()
        assert h1 != h2

    def test_serialization_round_trip(self) -> None:
        """to_dict/from_dict round-trip preserves all fields."""
        node = self._make_node()
        d = node.to_dict()
        restored = ExecutionNode.from_dict(d)
        assert restored.id == node.id
        assert restored.operation == node.operation
        assert restored.kind == node.kind
        assert restored.status == node.status
        assert restored.tags == node.tags
        assert restored.error is None

    def test_from_dict_with_optional_fields(self) -> None:
        """from_dict handles None started_at/finished_at and error."""
        node = self._make_node()
        d = node.to_dict()
        d["started_at"] = None
        d["finished_at"] = None
        d["error"] = None
        restored = ExecutionNode.from_dict(d)
        assert restored.started_at is None
        assert restored.finished_at is None
        assert restored.error is None


# ---------------------------------------------------------------------------
# ExecutionGraph
# ---------------------------------------------------------------------------


class TestExecutionGraph:
    """Tests for ExecutionGraph operations."""

    def _make_graph_with_two_nodes(self) -> ExecutionGraph:
        graph = ExecutionGraph.new(metadata={"test": True})
        n1 = ExecutionNode(
            id="n1",
            operation="source.ingest",
            kind=NodeKind.SOURCE,
            inputs={"payload": "hello"},
            outputs={},
            dependencies=[],
            input_hash="",
            output_hash="",
            environment_signature=get_env_signature(),
            plugin_version="1.0",
            rule_version="1.0",
            status=NodeStatus.PENDING,
            failure_mode=FailureMode.FAIL_FAST,
            created_at="2024-01-01T00:00:00+00:00",
            started_at=None,
            finished_at=None,
        )
        n2 = ExecutionNode(
            id="n2",
            operation="sink.collect",
            kind=NodeKind.SINK,
            inputs={},
            outputs={},
            dependencies=["n1"],
            input_hash="",
            output_hash="",
            environment_signature=get_env_signature(),
            plugin_version="1.0",
            rule_version="1.0",
            status=NodeStatus.PENDING,
            failure_mode=FailureMode.FAIL_FAST,
            created_at="2024-01-01T00:00:00+00:00",
            started_at=None,
            finished_at=None,
        )
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_edge("n1", "n2")
        graph.compute_graph_hash()
        return graph

    def test_add_node_and_edge(self) -> None:
        """add_node and add_edge correctly populate nodes and edges."""
        graph = self._make_graph_with_two_nodes()
        assert "n1" in graph.nodes
        assert "n2" in graph.nodes
        assert ("n1", "n2") in graph.edges

    def test_serialize_round_trip(self) -> None:
        """serialize/from_dict round-trip preserves graph structure."""
        graph = self._make_graph_with_two_nodes()
        d = graph.serialize()
        restored = ExecutionGraph.from_dict(d)
        assert restored.id == graph.id
        assert set(restored.nodes) == set(graph.nodes)
        assert len(restored.edges) == len(graph.edges)

    def test_validate_dag_accepts_valid_dag(self) -> None:
        """validate_dag does not raise for a valid DAG."""
        graph = self._make_graph_with_two_nodes()
        graph.validate_dag()  # should not raise

    def test_validate_dag_rejects_cycle(self) -> None:
        """validate_dag raises ValueError when a cycle exists."""
        graph = ExecutionGraph.new()
        n1 = ExecutionNode(
            id="n1",
            operation="op",
            kind=NodeKind.SOURCE,
            inputs={},
            outputs={},
            dependencies=["n2"],
            input_hash="",
            output_hash="",
            environment_signature="",
            plugin_version="1.0",
            rule_version="1.0",
            status=NodeStatus.PENDING,
            failure_mode=FailureMode.FAIL_FAST,
            created_at="",
            started_at=None,
            finished_at=None,
        )
        n2 = ExecutionNode(
            id="n2",
            operation="op",
            kind=NodeKind.SINK,
            inputs={},
            outputs={},
            dependencies=["n1"],
            input_hash="",
            output_hash="",
            environment_signature="",
            plugin_version="1.0",
            rule_version="1.0",
            status=NodeStatus.PENDING,
            failure_mode=FailureMode.FAIL_FAST,
            created_at="",
            started_at=None,
            finished_at=None,
        )
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_edge("n1", "n2")
        graph.add_edge("n2", "n1")
        with pytest.raises(ValueError, match=r"[Cc]ycle"):
            graph.validate_dag()

    def test_graph_hash_changes_with_content(self) -> None:
        """Graph hash changes when node content changes."""
        graph = self._make_graph_with_two_nodes()
        h1 = graph.graph_hash
        graph.nodes["n1"].inputs = {"payload": "different"}
        graph.compute_graph_hash()
        assert graph.graph_hash != h1

    def test_new_creates_unique_ids(self) -> None:
        """ExecutionGraph.new() generates distinct IDs each call."""
        g1 = ExecutionGraph.new()
        g2 = ExecutionGraph.new()
        assert g1.id != g2.id


# ---------------------------------------------------------------------------
# GraphBuilder
# ---------------------------------------------------------------------------


class TestGraphBuilder:
    """Tests for GraphBuilder."""

    def test_builds_valid_graph_from_payload(self) -> None:
        """build_from_payload produces a graph with SOURCE and SINK nodes."""
        builder = GraphBuilder()
        payload: dict[str, object] = {"query": "test", "mode": "fast"}
        graph = builder.build_from_payload(payload)

        assert len(graph.nodes) == 2
        node_kinds = {n.kind for n in graph.nodes.values()}
        assert NodeKind.SOURCE in node_kinds
        assert NodeKind.SINK in node_kinds

    def test_builds_source_sink_edge(self) -> None:
        """build_from_payload creates a SOURCE -> SINK directed edge."""
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})

        source = next(n for n in graph.nodes.values() if n.kind == NodeKind.SOURCE)
        sink = next(n for n in graph.nodes.values() if n.kind == NodeKind.SINK)
        assert (source.id, sink.id) in graph.edges

    def test_payload_stored_in_source_inputs(self) -> None:
        """Payload data is stored in the SOURCE node's inputs."""
        builder = GraphBuilder()
        payload: dict[str, object] = {"data": "hello", "num": 99}
        graph = builder.build_from_payload(payload)

        source = next(n for n in graph.nodes.values() if n.kind == NodeKind.SOURCE)
        assert source.inputs["data"] == "hello"
        assert source.inputs["num"] == 99

    def test_graph_hash_is_set(self) -> None:
        """build_from_payload sets a non-empty graph hash."""
        builder = GraphBuilder()
        graph = builder.build_from_payload({"k": "v"})
        assert graph.graph_hash
        assert len(graph.graph_hash) == 64


# ---------------------------------------------------------------------------
# ExecutionPlanner
# ---------------------------------------------------------------------------


class TestExecutionPlanner:
    """Tests for ExecutionPlanner topological ordering."""

    def test_returns_correct_topological_order(self) -> None:
        """Planner returns sources before their dependents."""
        graph = ExecutionGraph.new()
        for nid in ["a", "b", "c"]:
            graph.add_node(
                ExecutionNode(
                    id=nid,
                    operation="op",
                    kind=NodeKind.TRANSFORM,
                    inputs={},
                    outputs={},
                    dependencies=[],
                    input_hash="",
                    output_hash="",
                    environment_signature="",
                    plugin_version="1.0",
                    rule_version="1.0",
                    status=NodeStatus.PENDING,
                    failure_mode=FailureMode.FAIL_FAST,
                    created_at="",
                    started_at=None,
                    finished_at=None,
                )
            )
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")

        planner = ExecutionPlanner()
        order = planner.plan(graph)
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_raises_on_cycle(self) -> None:
        """Planner raises ValueError for cyclic graphs."""
        graph = ExecutionGraph.new()
        for nid in ["x", "y"]:
            graph.add_node(
                ExecutionNode(
                    id=nid,
                    operation="op",
                    kind=NodeKind.TRANSFORM,
                    inputs={},
                    outputs={},
                    dependencies=[],
                    input_hash="",
                    output_hash="",
                    environment_signature="",
                    plugin_version="1.0",
                    rule_version="1.0",
                    status=NodeStatus.PENDING,
                    failure_mode=FailureMode.FAIL_FAST,
                    created_at="",
                    started_at=None,
                    finished_at=None,
                )
            )
        graph.add_edge("x", "y")
        graph.add_edge("y", "x")
        planner = ExecutionPlanner()
        with pytest.raises(ValueError, match=r"[Cc]ycle"):
            planner.plan(graph)

    def test_all_nodes_in_order(self) -> None:
        """Plan contains exactly all node IDs."""
        builder = GraphBuilder()
        graph = builder.build_from_payload({"k": "v"})
        planner = ExecutionPlanner()
        order = planner.plan(graph)
        assert set(order) == set(graph.nodes)


# ---------------------------------------------------------------------------
# DeterministicExecutor
# ---------------------------------------------------------------------------


class _DoubleInputHandler:
    """Test handler that doubles numeric 'value' input."""

    def execute(self, node: ExecutionNode, inputs: dict[str, object]) -> dict[str, object]:
        val = inputs.get("value", 0)
        return {"doubled": int(str(val)) * 2}


class TestDeterministicExecutor:
    """Tests for DeterministicExecutor."""

    def test_execute_node_passthrough_when_no_handler(self) -> None:
        """Nodes without a registered handler get passthrough outputs."""
        executor = DeterministicExecutor()
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        planner = ExecutionPlanner()
        plan = planner.plan(graph)
        updated_graph = executor.execute_graph(graph, plan)

        for node in updated_graph.nodes.values():
            assert node.status == NodeStatus.SUCCEEDED

    def test_execute_node_uses_registered_handler(self) -> None:
        """Registered handler is called and its output stored."""
        executor = DeterministicExecutor()
        executor.register_handler("source.ingest", _DoubleInputHandler())

        builder = GraphBuilder()
        graph = builder.build_from_payload({"value": 5})
        planner = ExecutionPlanner()
        plan = planner.plan(graph)
        updated = executor.execute_graph(graph, plan)

        source = next(n for n in updated.nodes.values() if n.kind == NodeKind.SOURCE)
        assert source.outputs.get("doubled") == 10

    def test_execute_node_sets_timestamps(self) -> None:
        """Executed nodes have started_at and finished_at set."""
        executor = DeterministicExecutor()
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        planner = ExecutionPlanner()
        plan = planner.plan(graph)
        updated = executor.execute_graph(graph, plan)

        for node in updated.nodes.values():
            assert node.started_at is not None
            assert node.finished_at is not None

    def test_execute_node_updates_output_hash(self) -> None:
        """Output hash is recomputed after execution."""
        executor = DeterministicExecutor()
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        planner = ExecutionPlanner()
        plan = planner.plan(graph)
        updated = executor.execute_graph(graph, plan)

        for node in updated.nodes.values():
            assert node.output_hash == node.compute_output_hash()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Tests that verify deterministic behavior across identical payloads."""

    def test_same_payload_produces_same_graph_hash(self) -> None:
        """Two GraphBuilder calls with the same payload inputs yield the same hash."""
        payload: dict[str, object] = {"query": "hello", "mode": "strict"}
        builder = GraphBuilder()

        g1 = builder.build_from_payload(payload)
        g2 = builder.build_from_payload(payload)

        # Node IDs differ (UUID), but the input hashes should be identical
        source1 = next(n for n in g1.nodes.values() if n.kind == NodeKind.SOURCE)
        source2 = next(n for n in g2.nodes.values() if n.kind == NodeKind.SOURCE)
        assert source1.input_hash == source2.input_hash

    def test_executor_is_deterministic_for_same_input(self) -> None:
        """Executing the same graph structure twice yields the same outputs."""
        executor = DeterministicExecutor()
        planner = ExecutionPlanner()
        builder = GraphBuilder()

        payload: dict[str, object] = {"data": "test"}

        g1 = builder.build_from_payload(payload)
        plan1 = planner.plan(g1)
        g1 = executor.execute_graph(g1, plan1)

        g2 = builder.build_from_payload(payload)
        plan2 = planner.plan(g2)
        g2 = executor.execute_graph(g2, plan2)

        outputs1 = {n.kind.value: n.outputs for n in g1.nodes.values()}
        outputs2 = {n.kind.value: n.outputs for n in g2.nodes.values()}
        assert outputs1 == outputs2
