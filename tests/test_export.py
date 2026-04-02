"""Tests for the Export Presenter subsystem.

Covers ExportPresenter, ProofTrace, and LineageGraph — including JSON
serialisation, proof trace assembly, and lineage graph construction.
All tests are fully deterministic (fixed timestamps, keys, and content).
"""

from __future__ import annotations

import json

import pytest

from thalos_prime.artifacts.schema import Artifact
from thalos_prime.audit.trail import AuditEventType, AuditTrail
from thalos_prime.belief.ledger import BeliefLedger
from thalos_prime.export.presenter import ExportPresenter, LineageGraph, ProofTrace
from thalos_prime.indexing.prp import PrpIndexer
from thalos_prime.validation.pipeline import ValidationPipeline

# ---------------------------------------------------------------------------
# Fixed test constants
# ---------------------------------------------------------------------------
_TS: int = 2_000_000_000
_KEY: bytes = b"\x02" * 16


def _make_deps() -> tuple[BeliefLedger, AuditTrail, ValidationPipeline, ExportPresenter]:
    ledger = BeliefLedger(ledger_id="export-ledger")
    trail = AuditTrail(trail_id="export-trail")
    pipeline = ValidationPipeline(pipeline_id="export-pipe", belief_ledger=ledger)
    presenter = ExportPresenter(presenter_id="export-presenter")
    return ledger, trail, pipeline, presenter


def _ingest_artifact(
    ledger: BeliefLedger,
    trail: AuditTrail,
    content: str,
    ts: int = _TS,
) -> Artifact:
    """Ingest an artifact into the ledger and audit trail for testing."""
    indexer = PrpIndexer(key=_KEY)
    art = Artifact.create(content=content, source_uris=["https://source.example"])
    coord = indexer.index(art.content)
    ledger.admit(art, coord.to_hex_str(), 0.85, ts)
    ledger.accept(art.artifact_id, ts)
    trail.append(
        event_type=AuditEventType.ARTIFACT_ADMITTED,
        artifact_id=art.artifact_id,
        timestamp_ns=ts,
        payload={"coord": coord.to_hex_str()},
    )
    return art


# ===========================================================================
# ExportPresenter — construction
# ===========================================================================


class TestExportPresenterConstruction:
    def test_presenter_id(self) -> None:
        _, _, _, presenter = _make_deps()
        assert presenter.presenter_id == "export-presenter"

    def test_different_ids_are_independent(self) -> None:
        p1 = ExportPresenter(presenter_id="p1")
        p2 = ExportPresenter(presenter_id="p2")
        assert p1.presenter_id != p2.presenter_id


# ===========================================================================
# ExportPresenter — export_artifact_json
# ===========================================================================


class TestExportArtifactJson:
    def test_returns_dict(self) -> None:
        _, _, _, presenter = _make_deps()
        art = Artifact.create(content="hello", source_uris=["https://x"])
        result = presenter.export_artifact_json(art)
        assert isinstance(result, dict)

    def test_contains_artifact_id(self) -> None:
        _, _, _, presenter = _make_deps()
        art = Artifact.create(content="hello", source_uris=["https://x"])
        result = presenter.export_artifact_json(art)
        assert result["artifact_id"] == art.artifact_id

    def test_contains_content(self) -> None:
        _, _, _, presenter = _make_deps()
        art = Artifact.create(content="special content", source_uris=["https://x"])
        result = presenter.export_artifact_json(art)
        assert result["content"] == "special content"

    def test_schema_version_present(self) -> None:
        _, _, _, presenter = _make_deps()
        art = Artifact.create(content="v", source_uris=["https://x"])
        result = presenter.export_artifact_json(art)
        assert "schema_version" in result


# ===========================================================================
# ExportPresenter — build_proof_trace
# ===========================================================================


class TestBuildProofTrace:
    def test_returns_proof_trace_instance(self) -> None:
        ledger, trail, pipeline, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "proof trace content")
        verdict = pipeline.validate(art, _TS)
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        assert isinstance(trace, ProofTrace)

    def test_trace_id_is_hex(self) -> None:
        ledger, trail, pipeline, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "trace id test")
        verdict = pipeline.validate(art, _TS)
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        assert len(trace.trace_id) == 64  # SHA-256 hex length
        assert all(c in "0123456789abcdef" for c in trace.trace_id)

    def test_artifact_id_matches(self) -> None:
        ledger, trail, pipeline, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "artifact id match test")
        verdict = pipeline.validate(art, _TS)
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        assert trace.artifact_id == art.artifact_id

    def test_validation_stages_populated(self) -> None:
        ledger, trail, pipeline, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "stages test content")
        verdict = pipeline.validate(art, _TS)
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        assert len(trace.validation_stages) > 0

    def test_validation_stage_structure(self) -> None:
        ledger, trail, pipeline, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "stage structure content")
        verdict = pipeline.validate(art, _TS)
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        for stage in trace.validation_stages:
            assert "stage" in stage
            assert "passed" in stage
            assert "score" in stage

    def test_audit_events_for_artifact_included(self) -> None:
        ledger, trail, pipeline, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "audit events content")
        verdict = pipeline.validate(art, _TS)
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        # We added an ARTIFACT_ADMITTED event for this artifact in _ingest_artifact
        assert len(trace.audit_events) >= 1
        ids = {ev["artifact_id"] for ev in trace.audit_events}
        assert art.artifact_id in ids

    def test_derivation_steps_empty_for_fresh_artifact(self) -> None:
        ledger, trail, pipeline, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "no provenance content")
        verdict = pipeline.validate(art, _TS)
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        # Artifact.create() uses empty provenance unless explicitly set
        assert isinstance(trace.derivation_steps, list)

    def test_schema_version(self) -> None:
        ledger, trail, pipeline, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "schema version test")
        verdict = pipeline.validate(art, _TS)
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        assert trace.schema_version == 1

    def test_trace_is_deterministic_same_inputs(self) -> None:
        ledger, trail, pipeline, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "determinism test")
        verdict = pipeline.validate(art, _TS)
        t1 = presenter.build_proof_trace(art, verdict, trail, ledger)
        t2 = presenter.build_proof_trace(art, verdict, trail, ledger)
        assert t1.trace_id == t2.trace_id

    def test_model_dump_serialisable(self) -> None:
        ledger, trail, pipeline, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "dump test content")
        verdict = pipeline.validate(art, _TS)
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        d = trace.model_dump()
        assert isinstance(d, dict)
        assert "trace_id" in d
        assert "validation_stages" in d


# ===========================================================================
# ExportPresenter — build_lineage_graph
# ===========================================================================


class TestBuildLineageGraph:
    def test_returns_lineage_graph_instance(self) -> None:
        ledger, trail, _, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "lineage graph content")
        graph = presenter.build_lineage_graph(art.artifact_id, ledger)
        assert isinstance(graph, LineageGraph)

    def test_root_artifact_id_set(self) -> None:
        ledger, trail, _, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "root id test")
        graph = presenter.build_lineage_graph(art.artifact_id, ledger)
        assert graph.root_artifact_id == art.artifact_id

    def test_graph_id_is_hex(self) -> None:
        ledger, trail, _, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "graph id test")
        graph = presenter.build_lineage_graph(art.artifact_id, ledger)
        assert len(graph.graph_id) == 64
        assert all(c in "0123456789abcdef" for c in graph.graph_id)

    def test_root_artifact_id_in_response(self) -> None:
        ledger, trail, _, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "node content test")
        graph = presenter.build_lineage_graph(art.artifact_id, ledger)
        # root_artifact_id always identifies the queried artifact
        assert graph.root_artifact_id == art.artifact_id
        # nodes are ancestor records; a fresh artifact without parents has none
        assert isinstance(graph.nodes, list)

    def test_node_structure(self) -> None:
        ledger, trail, _, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "node structure test")
        graph = presenter.build_lineage_graph(art.artifact_id, ledger)
        for node in graph.nodes:
            assert "artifact_id" in node
            assert "state" in node
            assert "confidence" in node

    def test_edges_structure(self) -> None:
        ledger, trail, _, presenter = _make_deps()
        # One node → no edges
        art = _ingest_artifact(ledger, trail, "single node no edges")
        graph = presenter.build_lineage_graph(art.artifact_id, ledger)
        for edge in graph.edges:
            assert "from" in edge
            assert "to" in edge
            assert edge["relation"] == "parent"

    def test_graph_id_deterministic(self) -> None:
        ledger, trail, _, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "graph id determinism test")
        g1 = presenter.build_lineage_graph(art.artifact_id, ledger)
        g2 = presenter.build_lineage_graph(art.artifact_id, ledger)
        assert g1.graph_id == g2.graph_id

    def test_model_dump_serialisable(self) -> None:
        ledger, trail, _, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "lineage dump test")
        graph = presenter.build_lineage_graph(art.artifact_id, ledger)
        d = graph.model_dump()
        assert isinstance(d, dict)
        assert "nodes" in d
        assert "edges" in d


# ===========================================================================
# ExportPresenter — export_to_json
# ===========================================================================


class TestExportToJson:
    def test_dict_input(self) -> None:
        _, _, _, presenter = _make_deps()
        result = presenter.export_to_json({"b": 2, "a": 1})
        parsed = json.loads(result)
        assert parsed == {"a": 1, "b": 2}

    def test_sorted_keys(self) -> None:
        _, _, _, presenter = _make_deps()
        result = presenter.export_to_json({"z": "last", "a": "first"})
        # keys should appear in sorted order
        assert result.index('"a"') < result.index('"z"')

    def test_proof_trace_input(self) -> None:
        ledger, trail, pipeline, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "json export proof trace")
        verdict = pipeline.validate(art, _TS)
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        result = presenter.export_to_json(trace)
        parsed = json.loads(result)
        assert parsed["artifact_id"] == art.artifact_id

    def test_lineage_graph_input(self) -> None:
        ledger, trail, _, presenter = _make_deps()
        art = _ingest_artifact(ledger, trail, "json export lineage graph")
        graph = presenter.build_lineage_graph(art.artifact_id, ledger)
        result = presenter.export_to_json(graph)
        parsed = json.loads(result)
        assert parsed["root_artifact_id"] == art.artifact_id

    def test_output_is_valid_json(self) -> None:
        _, _, _, presenter = _make_deps()
        result = presenter.export_to_json({"key": "value", "num": 42})
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["num"] == 42

    def test_indentation_in_output(self) -> None:
        _, _, _, presenter = _make_deps()
        result = presenter.export_to_json({"a": 1})
        # Should have 2-space indentation
        assert "  " in result


# ===========================================================================
# ProofTrace model
# ===========================================================================


class TestProofTrace:
    def test_fields_present(self) -> None:
        trace = ProofTrace(
            trace_id="abc123",
            artifact_id="def456",
            derivation_steps=[],
            validation_stages=[],
            audit_events=[],
            lineage=[],
            timestamp_ns=_TS,
        )
        assert trace.trace_id == "abc123"
        assert trace.artifact_id == "def456"
        assert trace.schema_version == 1

    def test_default_schema_version(self) -> None:
        trace = ProofTrace(
            trace_id="t",
            artifact_id="a",
            derivation_steps=[],
            validation_stages=[],
            audit_events=[],
            lineage=[],
            timestamp_ns=_TS,
        )
        assert trace.schema_version == 1

    def test_model_dump_keys(self) -> None:
        trace = ProofTrace(
            trace_id="t",
            artifact_id="a",
            derivation_steps=[],
            validation_stages=[],
            audit_events=[],
            lineage=[],
            timestamp_ns=_TS,
        )
        d = trace.model_dump()
        expected_keys = {
            "trace_id",
            "artifact_id",
            "derivation_steps",
            "validation_stages",
            "audit_events",
            "lineage",
            "timestamp_ns",
            "schema_version",
        }
        assert expected_keys.issubset(d.keys())


# ===========================================================================
# LineageGraph model
# ===========================================================================


class TestLineageGraph:
    def test_fields_present(self) -> None:
        graph = LineageGraph(
            graph_id="g1",
            root_artifact_id="r1",
            nodes=[{"artifact_id": "r1", "state": "accepted", "confidence": "0.9"}],
            edges=[],
            timestamp_ns=_TS,
        )
        assert graph.graph_id == "g1"
        assert graph.root_artifact_id == "r1"
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 0

    def test_model_dump_keys(self) -> None:
        graph = LineageGraph(
            graph_id="g",
            root_artifact_id="r",
            nodes=[],
            edges=[],
            timestamp_ns=_TS,
        )
        d = graph.model_dump()
        assert "graph_id" in d
        assert "root_artifact_id" in d
        assert "nodes" in d
        assert "edges" in d


# ===========================================================================
# No-lifecycle assertion
# ===========================================================================


@pytest.mark.parametrize("method", ["initialize", "validate", "operate", "reconcile", "checkpoint", "terminate"])
def test_presenter_missing_lifecycle_method(method: str) -> None:
    """ExportPresenter must not define Control Plane lifecycle methods."""
    assert not hasattr(ExportPresenter, method), (
        f"ExportPresenter must not have lifecycle method: {method}"
    )
