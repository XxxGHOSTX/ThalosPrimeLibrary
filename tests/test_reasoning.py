"""Tests for the TPL Reasoning Layer subsystem.

Covers DeriveOperation, CandidateClaim, and TplReasoningLayer —
including all lifecycle methods, derivation paths, and error cases.
All tests are fully deterministic (fixed timestamps, keys, and content).
"""

from __future__ import annotations

import pytest

from thalos_prime.artifacts.schema import Artifact, ValidationStatus
from thalos_prime.audit.trail import AuditTrail
from thalos_prime.belief.ledger import BeliefLedger
from thalos_prime.reasoning_tpl.derive import (
    CandidateClaim,
    DeriveOperation,
    TplReasoningLayer,
)
from thalos_prime.validation.pipeline import ValidationPipeline

# ---------------------------------------------------------------------------
# Fixed test constants
# ---------------------------------------------------------------------------
_TS: int = 1_000_000_000
_KEY: bytes = b"\x01" * 16


def _make_layer() -> tuple[
    TplReasoningLayer,
    BeliefLedger,
    ValidationPipeline,
    AuditTrail,
]:
    """Create a fresh, initialised reasoning layer with dependencies."""
    ledger = BeliefLedger(ledger_id="test-ledger")
    trail = AuditTrail(trail_id="test-trail")
    pipeline = ValidationPipeline(pipeline_id="test-pipe", belief_ledger=ledger)
    layer = TplReasoningLayer(
        layer_id="test-layer",
        belief_ledger=ledger,
        validation_pipeline=pipeline,
        audit_trail=trail,
    )
    layer.initialize()
    return layer, ledger, pipeline, trail


def _admit_accepted(
    ledger: BeliefLedger,
    content: str,
    ts: int = _TS,
) -> Artifact:
    """Create an artifact, admit it, and accept it for testing."""
    from thalos_prime.indexing.prp import PrpIndexer

    art = Artifact.create(content=content, source_uris=["https://test.example"])
    indexer = PrpIndexer(key=_KEY)
    coord = indexer.index(art.content)
    ledger.admit(art, coord.to_hex_str(), 0.9, ts)
    ledger.accept(art.artifact_id, ts)
    return art


# ===========================================================================
# DeriveOperation
# ===========================================================================


class TestDeriveOperation:
    def test_all_members_present(self) -> None:
        values = {op.value for op in DeriveOperation}
        assert values == {"synthesize", "summarize", "extract", "infer", "combine"}

    def test_is_str_enum(self) -> None:
        assert isinstance(DeriveOperation.SYNTHESIZE, str)

    def test_construction_from_string(self) -> None:
        op = DeriveOperation("synthesize")
        assert op is DeriveOperation.SYNTHESIZE

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            DeriveOperation("unknown_op")


# ===========================================================================
# CandidateClaim
# ===========================================================================


class TestCandidateClaim:
    def test_fields(self) -> None:
        claim = CandidateClaim(
            claim_id="abc123",
            content="test content",
            operation="synthesize",
            source_artifact_ids=["id1", "id2"],
            derivation_log=[{"step": "input", "input": "id1", "output": "x", "timestamp_ns": "1"}],
            timestamp_ns=_TS,
        )
        assert claim.claim_id == "abc123"
        assert claim.content == "test content"
        assert claim.approved is False
        assert claim.schema_version == 1

    def test_approved_defaults_false(self) -> None:
        claim = CandidateClaim(
            claim_id="x",
            content="y",
            operation="infer",
            source_artifact_ids=[],
            derivation_log=[],
            timestamp_ns=_TS,
        )
        assert claim.approved is False

    def test_model_dump_serialisable(self) -> None:
        claim = CandidateClaim(
            claim_id="abc",
            content="data",
            operation="synthesize",
            source_artifact_ids=["a"],
            derivation_log=[],
            timestamp_ns=_TS,
        )
        d = claim.model_dump()
        assert d["claim_id"] == "abc"
        assert isinstance(d["source_artifact_ids"], list)


# ===========================================================================
# TplReasoningLayer — lifecycle
# ===========================================================================


class TestTplReasoningLayerLifecycle:
    def test_layer_id(self) -> None:
        layer, *_ = _make_layer()
        assert layer.layer_id == "test-layer"

    def test_initialize_sets_initialized(self) -> None:
        ledger = BeliefLedger(ledger_id="l")
        trail = AuditTrail(trail_id="t")
        pipeline = ValidationPipeline(pipeline_id="p", belief_ledger=ledger)
        layer = TplReasoningLayer("ly", ledger, pipeline, trail)
        assert layer.validate() is False
        layer.initialize()
        assert layer.validate() is True

    def test_terminate_clears_initialized(self) -> None:
        layer, *_ = _make_layer()
        assert layer.validate() is True
        layer.terminate()
        assert layer.validate() is False

    def test_reconcile_is_noop(self) -> None:
        layer, *_ = _make_layer()
        # Should not raise
        layer.reconcile()

    def test_checkpoint_structure(self) -> None:
        layer, *_ = _make_layer()
        cp = layer.checkpoint()
        assert cp["layer_id"] == "test-layer"
        assert cp["initialized"] is True
        assert cp["schema_version"] == 1

    def test_checkpoint_after_terminate(self) -> None:
        layer, *_ = _make_layer()
        layer.terminate()
        cp = layer.checkpoint()
        assert cp["initialized"] is False

    def test_schema_version_class_var(self) -> None:
        assert TplReasoningLayer.schema_version == 1


# ===========================================================================
# TplReasoningLayer — derive
# ===========================================================================


class TestTplReasoningLayerDerive:
    def test_derive_missing_ids_raises(self) -> None:
        layer, *_ = _make_layer()
        with pytest.raises(ValueError, match="not found or not ACCEPTED"):
            layer.derive(["nonexistent"], DeriveOperation.SYNTHESIZE, _TS)

    def test_derive_non_accepted_raises(self) -> None:
        layer, ledger, *_ = _make_layer()
        from thalos_prime.indexing.prp import PrpIndexer

        art = Artifact.create(content="pending content", source_uris=["https://x"])
        indexer = PrpIndexer(key=_KEY)
        coord = indexer.index(art.content)
        ledger.admit(art, coord.to_hex_str(), 0.5, _TS)
        # NOT accepted → still PENDING
        with pytest.raises(ValueError, match="not found or not ACCEPTED"):
            layer.derive([art.artifact_id], DeriveOperation.SYNTHESIZE, _TS)

    def test_derive_synthesize_returns_candidate(self) -> None:
        layer, ledger, *_ = _make_layer()
        art = _admit_accepted(ledger, "content for synthesize test")
        candidate, _verdict = layer.derive(
            [art.artifact_id], DeriveOperation.SYNTHESIZE, _TS
        )
        assert isinstance(candidate, CandidateClaim)
        assert candidate.operation == "synthesize"
        assert art.artifact_id in candidate.source_artifact_ids
        assert candidate.approved is False

    def test_derive_summarize(self) -> None:
        layer, ledger, *_ = _make_layer()
        art = _admit_accepted(ledger, "A" * 300)
        candidate, _verdict = layer.derive(
            [art.artifact_id], DeriveOperation.SUMMARIZE, _TS
        )
        # SUMMARIZE takes the first 200 chars (of coordinate_hex proxy in derive)
        assert candidate.operation == "summarize"
        assert len(candidate.content) <= 200

    def test_derive_infer(self) -> None:
        layer, ledger, *_ = _make_layer()
        art = _admit_accepted(ledger, "quantum entanglement describes correlation")
        candidate, _verdict = layer.derive(
            [art.artifact_id], DeriveOperation.INFER, _TS
        )
        assert candidate.operation == "infer"
        assert candidate.content.startswith("Inferred:")

    def test_derive_extract(self) -> None:
        layer, ledger, *_ = _make_layer()
        art = _admit_accepted(
            ledger,
            "First sentence here. Second sentence that is long enough. Third sentence too.",
        )
        candidate, _verdict = layer.derive(
            [art.artifact_id], DeriveOperation.EXTRACT, _TS
        )
        assert candidate.operation == "extract"

    def test_derive_combine_multiple(self) -> None:
        layer, ledger, *_ = _make_layer()
        art1 = _admit_accepted(ledger, "alpha content", _TS)
        art2 = _admit_accepted(ledger, "beta content", _TS + 1)
        candidate, _verdict = layer.derive(
            [art1.artifact_id, art2.artifact_id], DeriveOperation.COMBINE, _TS + 2
        )
        assert candidate.operation == "combine"
        assert len(candidate.source_artifact_ids) == 2

    def test_derive_claim_id_deterministic(self) -> None:
        layer, ledger, *_ = _make_layer()
        art = _admit_accepted(ledger, "determinism test content")
        c1, _ = layer.derive([art.artifact_id], DeriveOperation.SYNTHESIZE, _TS)
        c2, _ = layer.derive([art.artifact_id], DeriveOperation.SYNTHESIZE, _TS)
        assert c1.claim_id == c2.claim_id

    def test_derive_logs_to_audit_trail(self) -> None:
        from thalos_prime.audit.trail import AuditEventType

        layer, ledger, _, trail = _make_layer()
        art = _admit_accepted(ledger, "audit trail test content")
        layer.derive([art.artifact_id], DeriveOperation.SYNTHESIZE, _TS)
        derivation_events = trail.get_events(event_type=AuditEventType.DERIVATION_STEP)
        assert len(derivation_events) >= 1

    def test_derive_verdict_has_status(self) -> None:

        layer, ledger, *_ = _make_layer()
        art = _admit_accepted(ledger, "verdict status test")
        _candidate, verdict = layer.derive(
            [art.artifact_id], DeriveOperation.SYNTHESIZE, _TS
        )
        assert verdict.final_status in list(ValidationStatus)

    def test_operate_is_alias_for_derive(self) -> None:
        layer, ledger, *_ = _make_layer()
        art = _admit_accepted(ledger, "operate alias test")
        c1, v1 = layer.derive([art.artifact_id], DeriveOperation.SYNTHESIZE, _TS)
        c2, v2 = layer.operate([art.artifact_id], DeriveOperation.SYNTHESIZE, _TS)
        assert c1.claim_id == c2.claim_id
        assert v1.final_status == v2.final_status

    def test_derive_derivation_log_contains_inputs(self) -> None:
        layer, ledger, *_ = _make_layer()
        art = _admit_accepted(ledger, "log entry test content")
        candidate, _ = layer.derive(
            [art.artifact_id], DeriveOperation.SYNTHESIZE, _TS
        )
        # derivation_log from _derive_claim records input steps
        assert len(candidate.derivation_log) >= 1
        first = candidate.derivation_log[0]
        assert first["step"] == "input"
        assert "input" in first
        assert "timestamp_ns" in first
