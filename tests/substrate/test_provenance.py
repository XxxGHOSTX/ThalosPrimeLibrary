"""Tests for provenance index and provenance graph."""

from __future__ import annotations

import tempfile
from pathlib import Path

from thalos_prime.execution_ir.builder import GraphBuilder
from thalos_prime.execution_ir.executor import DeterministicExecutor
from thalos_prime.execution_ir.planner import ExecutionPlanner
from thalos_prime.provenance.graph import ProvenanceEdge, ProvenanceGraph
from thalos_prime.provenance.index import ProvenanceIndex


class TestProvenanceIndex:
    """Tests for ProvenanceIndex node recording and retrieval."""

    def test_record_node_creates_provenance_record(self) -> None:
        """record_node creates a ProvenanceRecord with correct fields."""
        with tempfile.TemporaryDirectory() as tmp:
            index = ProvenanceIndex(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"x": 1})

            executor = DeterministicExecutor()
            planner = ExecutionPlanner()
            plan = planner.plan(graph)
            graph = executor.execute_graph(graph, plan)

            for node in graph.nodes.values():
                index.record_node(graph.id, node)

            records = index.get_by_graph(graph.id)
            assert len(records) == len(graph.nodes)

    def test_every_node_has_provenance_record_after_execution(self) -> None:
        """After execution, every node has a ProvenanceRecord."""
        with tempfile.TemporaryDirectory() as tmp:
            index = ProvenanceIndex(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"q": "test"})

            executor = DeterministicExecutor()
            planner = ExecutionPlanner()
            plan = planner.plan(graph)
            graph = executor.execute_graph(graph, plan)

            for node in graph.nodes.values():
                index.record_node(graph.id, node)

            for node_id in graph.nodes:
                record = index.get_by_node(graph.id, node_id)
                assert record is not None
                assert record.node_id == node_id

    def test_provenance_record_has_input_hash(self) -> None:
        """ProvenanceRecord stores a non-empty input_hash."""
        with tempfile.TemporaryDirectory() as tmp:
            index = ProvenanceIndex(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"q": "test"})

            executor = DeterministicExecutor()
            planner = ExecutionPlanner()
            plan = planner.plan(graph)
            graph = executor.execute_graph(graph, plan)

            node = next(iter(graph.nodes.values()))
            record = index.record_node(graph.id, node)
            assert record.input_hash
            assert len(record.input_hash) == 64

    def test_provenance_record_has_output_hash(self) -> None:
        """ProvenanceRecord stores a non-empty output_hash after execution."""
        with tempfile.TemporaryDirectory() as tmp:
            index = ProvenanceIndex(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"q": "test"})

            executor = DeterministicExecutor()
            planner = ExecutionPlanner()
            plan = planner.plan(graph)
            graph = executor.execute_graph(graph, plan)

            node = next(iter(graph.nodes.values()))
            record = index.record_node(graph.id, node)
            assert record.output_hash
            assert len(record.output_hash) == 64

    def test_provenance_record_has_environment_signature(self) -> None:
        """ProvenanceRecord stores the execution environment signature."""
        with tempfile.TemporaryDirectory() as tmp:
            index = ProvenanceIndex(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"x": 1})

            executor = DeterministicExecutor()
            planner = ExecutionPlanner()
            plan = planner.plan(graph)
            graph = executor.execute_graph(graph, plan)

            node = next(iter(graph.nodes.values()))
            record = index.record_node(graph.id, node)
            assert record.environment_signature
            assert len(record.environment_signature) == 64

    def test_get_by_node_returns_none_for_missing(self) -> None:
        """get_by_node returns None for an unrecorded node."""
        with tempfile.TemporaryDirectory() as tmp:
            index = ProvenanceIndex(base_path=Path(tmp))
            result = index.get_by_node("graph-x", "node-x")
            assert result is None

    def test_get_by_graph_empty_for_unknown_graph(self) -> None:
        """get_by_graph returns empty list for an untracked graph."""
        with tempfile.TemporaryDirectory() as tmp:
            index = ProvenanceIndex(base_path=Path(tmp))
            assert index.get_by_graph("unknown") == []


class TestProvenanceGraph:
    """Tests for in-memory ProvenanceGraph."""

    def test_add_edge_and_get_parents(self) -> None:
        """add_edge records parent-child relationship."""
        pg = ProvenanceGraph()
        edge = ProvenanceEdge(
            parent_node_id="parent",
            child_node_id="child",
            graph_id="g1",
        )
        pg.add_edge(edge)
        assert "parent" in pg.get_parents("child")

    def test_get_children(self) -> None:
        """get_children returns nodes that depend on the given node."""
        pg = ProvenanceGraph()
        pg.add_edge(ProvenanceEdge("n1", "n2", "g1"))
        pg.add_edge(ProvenanceEdge("n1", "n3", "g1"))
        children = pg.get_children("n1")
        assert "n2" in children
        assert "n3" in children

    def test_to_dict_contains_edges(self) -> None:
        """to_dict serializes all edges."""
        pg = ProvenanceGraph()
        pg.add_edge(ProvenanceEdge("a", "b", "g1"))
        pg.add_edge(ProvenanceEdge("b", "c", "g1"))
        d = pg.to_dict()
        assert isinstance(d["edges"], list)
        assert len(d["edges"]) == 2

    def test_get_parents_empty_for_root_node(self) -> None:
        """get_parents returns empty list for nodes with no recorded parents."""
        pg = ProvenanceGraph()
        assert pg.get_parents("root") == []
