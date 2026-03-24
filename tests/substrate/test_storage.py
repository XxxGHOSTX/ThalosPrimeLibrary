"""Tests for storage: LocalGraphStore, EventLog, VersionIndex."""

from __future__ import annotations

import tempfile
from pathlib import Path

from thalos_prime.execution_ir.builder import GraphBuilder
from thalos_prime.execution_ir.executor import DeterministicExecutor
from thalos_prime.execution_ir.planner import ExecutionPlanner
from thalos_prime.storage.event_log import EventLog, LogEvent
from thalos_prime.storage.graph_store import LocalGraphStore
from thalos_prime.storage.version_index import VersionIndex


class TestLocalGraphStore:
    """Tests for LocalGraphStore persistence."""

    def test_save_and_load_round_trip(self) -> None:
        """save/load correctly persists and restores a graph."""
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalGraphStore(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"key": "value"})

            store.save(graph)
            loaded = store.load(graph.id)

            assert loaded.id == graph.id
            assert loaded.graph_hash == graph.graph_hash
            assert set(loaded.nodes) == set(graph.nodes)

    def test_load_latest_version(self) -> None:
        """Loading without a version returns the highest-numbered version."""
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalGraphStore(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"x": 1})

            graph.version = 1
            store.save(graph)
            graph.version = 2
            store.save(graph)

            loaded = store.load(graph.id)
            assert loaded.version == 2

    def test_load_specific_version(self) -> None:
        """Loading with a version number returns that exact version."""
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalGraphStore(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"x": 1})

            graph.version = 1
            store.save(graph)
            graph.version = 2
            store.save(graph)

            loaded = store.load(graph.id, version=1)
            assert loaded.version == 1

    def test_list_ids_returns_saved_graphs(self) -> None:
        """list_ids returns all saved graph IDs."""
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalGraphStore(base_path=Path(tmp))
            builder = GraphBuilder()

            g1 = builder.build_from_payload({"a": 1})
            g2 = builder.build_from_payload({"b": 2})
            store.save(g1)
            store.save(g2)

            ids = store.list_ids()
            assert g1.id in ids
            assert g2.id in ids

    def test_load_nonexistent_raises(self) -> None:
        """Loading a missing graph raises FileNotFoundError."""
        import pytest
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalGraphStore(base_path=Path(tmp))
            with pytest.raises(FileNotFoundError):
                store.load("nonexistent-graph-id")

    def test_save_executed_graph_restores_node_statuses(self) -> None:
        """Node statuses are preserved through save/load."""
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalGraphStore(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"x": 1})

            executor = DeterministicExecutor()
            planner = ExecutionPlanner()
            plan = planner.plan(graph)
            graph = executor.execute_graph(graph, plan)

            store.save(graph)
            loaded = store.load(graph.id)

            from thalos_prime.execution_ir.node import NodeStatus
            for node in loaded.nodes.values():
                assert node.status == NodeStatus.SUCCEEDED


class TestEventLog:
    """Tests for EventLog append and retrieval."""

    def test_append_and_get_events(self) -> None:
        """Appended events are retrievable in order."""
        with tempfile.TemporaryDirectory() as tmp:
            log = EventLog(base_path=Path(tmp))
            log.log("created", "graph-1", 1, source="test")
            log.log("executed", "graph-1", 1, nodes=3)

            events = log.get_events("graph-1")
            assert len(events) == 2
            assert events[0].event_type == "created"
            assert events[1].event_type == "executed"

    def test_log_event_serialization(self) -> None:
        """LogEvent to_dict/from_dict round-trip is lossless."""
        event = LogEvent(
            event_type="test",
            graph_id="g1",
            timestamp="2024-01-01T00:00:00+00:00",
            version=1,
            payload={"key": "val"},
        )
        d = event.to_dict()
        restored = LogEvent.from_dict(d)
        assert restored.event_type == event.event_type
        assert restored.graph_id == event.graph_id
        assert restored.payload == event.payload

    def test_get_events_empty_for_unknown_graph(self) -> None:
        """get_events returns empty list for a graph with no events."""
        with tempfile.TemporaryDirectory() as tmp:
            log = EventLog(base_path=Path(tmp))
            assert log.get_events("no-such-graph") == []

    def test_events_are_isolated_by_graph_id(self) -> None:
        """Events for different graph IDs are stored separately."""
        with tempfile.TemporaryDirectory() as tmp:
            log = EventLog(base_path=Path(tmp))
            log.log("ev", "graph-A", 1)
            log.log("ev", "graph-B", 1)
            log.log("ev", "graph-B", 2)

            assert len(log.get_events("graph-A")) == 1
            assert len(log.get_events("graph-B")) == 2


class TestVersionIndex:
    """Tests for VersionIndex record and retrieval."""

    def test_record_and_get_versions(self) -> None:
        """record stores version metadata and get_versions retrieves it."""
        with tempfile.TemporaryDirectory() as tmp:
            index = VersionIndex(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"x": 1})

            index.record(graph)
            versions = index.get_versions(graph.id)

            assert len(versions) == 1
            assert versions[0].graph_id == graph.id
            assert versions[0].version == graph.version
            assert versions[0].graph_hash == graph.graph_hash

    def test_multiple_versions_recorded(self) -> None:
        """Multiple record() calls for the same graph accumulate versions."""
        with tempfile.TemporaryDirectory() as tmp:
            index = VersionIndex(base_path=Path(tmp))
            builder = GraphBuilder()
            graph = builder.build_from_payload({"x": 1})

            graph.version = 1
            index.record(graph)
            graph.version = 2
            index.record(graph)

            versions = index.get_versions(graph.id)
            assert len(versions) == 2
            assert {v.version for v in versions} == {1, 2}

    def test_get_children_returns_correct_children(self) -> None:
        """get_children returns graph IDs whose parent_id matches."""
        with tempfile.TemporaryDirectory() as tmp:
            index = VersionIndex(base_path=Path(tmp))
            builder = GraphBuilder()

            parent = builder.build_from_payload({"root": True})
            child = builder.build_from_payload({"child": True})
            child.parent_id = parent.id

            index.record(parent)
            index.record(child)

            children = index.get_children(parent.id)
            assert child.id in children

    def test_get_versions_empty_for_unknown_graph(self) -> None:
        """get_versions returns empty list for an untracked graph ID."""
        with tempfile.TemporaryDirectory() as tmp:
            index = VersionIndex(base_path=Path(tmp))
            assert index.get_versions("unknown-id") == []
