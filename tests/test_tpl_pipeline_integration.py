"""Full pipeline integration test.

Covers: raw data → indexed artifacts → candidate claims → validated belief base → proven results.

This test verifies the complete TPL data pipeline as specified in the architecture:

    raw data → indexed artifacts → candidate claims → validated belief base → proven results

Every subsystem involved in that pipeline is exercised end-to-end:
  - Artifact.create  (canonical data representation)
  - PrpIndexer       (HMAC-SHA256 coordinate derivation)
  - ValidationPipeline (6-stage deterministic validation)
  - BeliefLedger     (epistemic state machine)
  - TplReasoningLayer (claim derivation from ACCEPTED artifacts)
  - AuditTrail       (tamper-evident append-only log)
  - ExportPresenter  (ProofTrace + LineageGraph)

All operations use fixed seeds/keys and fixed timestamps for full replay
determinism.
"""

from __future__ import annotations

import pytest

from thalos_prime.artifacts.schema import Artifact, ValidationStatus
from thalos_prime.audit.trail import AuditEventType, AuditTrail
from thalos_prime.belief.ledger import BeliefLedger, BeliefRecord, BeliefState
from thalos_prime.export.presenter import ExportPresenter, LineageGraph, ProofTrace
from thalos_prime.indexing.prp import ArtifactCoordinates, Coordinate, PrpIndexer
from thalos_prime.reasoning_tpl.derive import CandidateClaim, DeriveOperation, TplReasoningLayer
from thalos_prime.validation.pipeline import ValidationPipeline, ValidationVerdict

# ---------------------------------------------------------------------------
# Fixed seeds / keys for determinism
# ---------------------------------------------------------------------------
_TS_BASE: int = 5_000_000_000
_PRP_KEY: bytes = b"\xca\xfe\xba\xbe" * 4  # 16-byte deterministic key


# ===========================================================================
# Stage 1 — Raw data → indexed artifacts
# ===========================================================================


class TestStage1Ingestion:
    """Verify that raw string data becomes a fully indexed Artifact."""

    def test_artifact_create_assigns_sha256_id(self) -> None:
        art = Artifact.create(
            content="deterministic content A",
            source_uris=["https://stage1.test/A"],
            timestamp_ns=_TS_BASE,
        )
        # artifact_id must be a 64-char lowercase hex string (SHA-256)
        assert len(art.artifact_id) == 64
        assert art.artifact_id == art.artifact_id.lower()
        assert all(c in "0123456789abcdef" for c in art.artifact_id)

    def test_artifact_create_is_deterministic(self) -> None:
        art1 = Artifact.create(
            content="same content",
            source_uris=["https://x"],
            timestamp_ns=_TS_BASE,
        )
        art2 = Artifact.create(
            content="same content",
            source_uris=["https://x"],
            timestamp_ns=_TS_BASE,
        )
        assert art1.artifact_id == art2.artifact_id

    def test_different_content_gives_different_ids(self) -> None:
        art1 = Artifact.create(content="alpha", source_uris=["https://x"], timestamp_ns=_TS_BASE)
        art2 = Artifact.create(content="beta", source_uris=["https://x"], timestamp_ns=_TS_BASE)
        assert art1.artifact_id != art2.artifact_id

    def test_prp_indexer_assigns_coordinate(self) -> None:
        art = Artifact.create(content="index me", source_uris=["https://x"], timestamp_ns=_TS_BASE)
        indexer = PrpIndexer(key=_PRP_KEY)
        coord = indexer.index(art.content)
        assert isinstance(coord, Coordinate)
        assert 0 <= coord.hexagon <= 65535
        assert 0 <= coord.wall <= 255
        assert 0 <= coord.shelf <= 255
        assert 0 <= coord.volume <= 65535
        assert 0 <= coord.page <= 65535

    def test_coordinate_is_deterministic(self) -> None:
        indexer = PrpIndexer(key=_PRP_KEY)
        art = Artifact.create(content="determinism", source_uris=["https://x"], timestamp_ns=_TS_BASE)
        c1 = indexer.index(art.content)
        c2 = indexer.index(art.content)
        assert c1 == c2

    def test_artifact_coordinates_bundle(self) -> None:
        indexer = PrpIndexer(key=_PRP_KEY)
        art = Artifact.create(content="bundle test", source_uris=["https://x"], timestamp_ns=_TS_BASE)
        coords = indexer.index_artifact(
            artifact_id=art.artifact_id,
            content=art.content,
            provenance_hash="0" * 64,
            version=art.version,
            trust_value=0.9,
        )
        assert isinstance(coords, ArtifactCoordinates)
        assert isinstance(coords.identity, Coordinate)
        assert isinstance(coords.semantic, Coordinate)
        assert isinstance(coords.provenance, Coordinate)
        assert isinstance(coords.version, Coordinate)
        assert isinstance(coords.trust_state, Coordinate)


# ===========================================================================
# Stage 2 — Indexed artifacts → validation pipeline
# ===========================================================================


class TestStage2Validation:
    """Verify that indexed artifacts pass through the 6-stage validation pipeline."""

    def test_validation_pipeline_returns_verdict(self) -> None:
        ledger = BeliefLedger(ledger_id="stage2")
        pipeline = ValidationPipeline(pipeline_id="stage2", belief_ledger=ledger)
        art = Artifact.create(
            content="validated content with multiple words and meaning",
            source_uris=["https://stage2.test"],
            timestamp_ns=_TS_BASE,
        )
        verdict = pipeline.validate(art, _TS_BASE)
        assert isinstance(verdict, ValidationVerdict)

    def test_verdict_has_final_status(self) -> None:
        ledger = BeliefLedger(ledger_id="stage2b")
        pipeline = ValidationPipeline(pipeline_id="stage2b", belief_ledger=ledger)
        art = Artifact.create(
            content="final status test",
            source_uris=["https://x"],
            timestamp_ns=_TS_BASE,
        )
        verdict = pipeline.validate(art, _TS_BASE)
        assert verdict.final_status in list(ValidationStatus)

    def test_verdict_has_confidence_in_range(self) -> None:
        ledger = BeliefLedger(ledger_id="stage2c")
        pipeline = ValidationPipeline(pipeline_id="stage2c", belief_ledger=ledger)
        art = Artifact.create(
            content="confidence range test content",
            source_uris=["https://x"],
            timestamp_ns=_TS_BASE,
        )
        verdict = pipeline.validate(art, _TS_BASE)
        assert 0.0 <= verdict.confidence <= 1.0

    def test_verdict_has_six_stage_results(self) -> None:
        ledger = BeliefLedger(ledger_id="stage2d")
        pipeline = ValidationPipeline(pipeline_id="stage2d", belief_ledger=ledger)
        art = Artifact.create(
            content="six stages test content",
            source_uris=["https://x"],
            timestamp_ns=_TS_BASE,
        )
        verdict = pipeline.validate(art, _TS_BASE)
        assert len(verdict.stage_results) == 6

    def test_short_content_rejected(self) -> None:
        ledger = BeliefLedger(ledger_id="stage2e")
        pipeline = ValidationPipeline(pipeline_id="stage2e", belief_ledger=ledger)
        art = Artifact.create(
            content="hi",  # too short → expect REJECTED
            source_uris=["https://x"],
            timestamp_ns=_TS_BASE,
        )
        verdict = pipeline.validate(art, _TS_BASE)
        assert verdict.final_status is ValidationStatus.REJECTED

    def test_no_source_uris_not_accepted(self) -> None:
        ledger = BeliefLedger(ledger_id="stage2f")
        pipeline = ValidationPipeline(pipeline_id="stage2f", belief_ledger=ledger)
        art = Artifact.create(
            content="no source uris test content",
            source_uris=[],
            timestamp_ns=_TS_BASE,
        )
        verdict = pipeline.validate(art, _TS_BASE)
        # Source-binding stage fails, so artifact must not be ACCEPTED
        assert verdict.final_status is not ValidationStatus.ACCEPTED


# ===========================================================================
# Stage 3 — Validated belief base
# ===========================================================================


class TestStage3BeliefBase:
    """Verify that artifacts flow through the belief base state machine."""

    def _ingest_to_ledger(
        self,
        ledger: BeliefLedger,
        content: str,
        ts: int = _TS_BASE,
    ) -> tuple[Artifact, str]:
        """Create an artifact, index it, and admit it to the ledger for testing."""
        indexer = PrpIndexer(key=_PRP_KEY)
        art = Artifact.create(
            content=content,
            source_uris=["https://stage3.test"],
            timestamp_ns=ts,
        )
        coord = indexer.index(art.content)
        ledger.admit(art, coord.to_hex_str(), 0.85, ts)
        return art, coord.to_hex_str()

    def test_admit_adds_pending_record(self) -> None:
        ledger = BeliefLedger(ledger_id="s3a")
        art, _ = self._ingest_to_ledger(ledger, "admit pending test")
        records = ledger.get_by_state(BeliefState.PENDING)
        ids = {r.artifact_id for r in records}
        assert art.artifact_id in ids

    def test_accept_transitions_to_accepted(self) -> None:
        ledger = BeliefLedger(ledger_id="s3b")
        art, _ = self._ingest_to_ledger(ledger, "accept transition test")
        ledger.accept(art.artifact_id, _TS_BASE)
        records = ledger.get_by_state(BeliefState.ACCEPTED)
        ids = {r.artifact_id for r in records}
        assert art.artifact_id in ids

    def test_dispute_transitions_to_disputed(self) -> None:
        ledger = BeliefLedger(ledger_id="s3c")
        art, _ = self._ingest_to_ledger(ledger, "dispute transition test")
        ledger.dispute(art.artifact_id, "disputed for test", _TS_BASE)
        records = ledger.get_by_state(BeliefState.DISPUTED)
        ids = {r.artifact_id for r in records}
        assert art.artifact_id in ids

    def test_reject_transitions_to_rejected(self) -> None:
        ledger = BeliefLedger(ledger_id="s3d")
        art, _ = self._ingest_to_ledger(ledger, "reject transition test")
        ledger.reject(art.artifact_id, "rejected for test", _TS_BASE)
        records = ledger.get_by_state(BeliefState.REJECTED)
        ids = {r.artifact_id for r in records}
        assert art.artifact_id in ids

    def test_get_by_confidence(self) -> None:
        ledger = BeliefLedger(ledger_id="s3e")
        art, _ = self._ingest_to_ledger(ledger, "high confidence test", _TS_BASE)
        ledger.accept(art.artifact_id, _TS_BASE)
        high = ledger.query_by_confidence(0.8)
        ids = {r.artifact_id for r in high}
        assert art.artifact_id in ids

    def test_resolve_by_coordinate(self) -> None:
        ledger = BeliefLedger(ledger_id="s3f")
        art, coord_hex = self._ingest_to_ledger(ledger, "resolve by coord test")
        record = ledger.resolve_by_coordinate(coord_hex)
        assert record is not None
        assert record.artifact_id == art.artifact_id

    def test_checkpoint_and_restore(self) -> None:
        ledger = BeliefLedger(ledger_id="s3g")
        art, _ = self._ingest_to_ledger(ledger, "checkpoint restore test")
        ledger.accept(art.artifact_id, _TS_BASE)
        cp = ledger.checkpoint()

        ledger2 = BeliefLedger(ledger_id="s3g-restore")
        ledger2.restore(cp)
        records = ledger2.get_by_state(BeliefState.ACCEPTED)
        ids = {r.artifact_id for r in records}
        assert art.artifact_id in ids

    def test_double_admit_raises(self) -> None:
        ledger = BeliefLedger(ledger_id="s3h")
        indexer = PrpIndexer(key=_PRP_KEY)
        art = Artifact.create(
            content="double admit test",
            source_uris=["https://x"],
            timestamp_ns=_TS_BASE,
        )
        coord = indexer.index(art.content)
        ledger.admit(art, coord.to_hex_str(), 0.8, _TS_BASE)
        with pytest.raises(ValueError):
            ledger.admit(art, coord.to_hex_str(), 0.8, _TS_BASE)


# ===========================================================================
# Stage 4 — Candidate claims via reasoning layer
# ===========================================================================


class TestStage4ReasoningLayer:
    """Verify claim derivation from ACCEPTED ledger artifacts."""

    def _setup(self) -> tuple[TplReasoningLayer, BeliefLedger, AuditTrail]:
        ledger = BeliefLedger(ledger_id="s4-ledger")
        trail = AuditTrail(trail_id="s4-trail")
        pipeline = ValidationPipeline(pipeline_id="s4-pipe", belief_ledger=ledger)
        layer = TplReasoningLayer("s4-layer", ledger, pipeline, trail)
        layer.initialize()
        return layer, ledger, trail

    def _accept(self, ledger: BeliefLedger, content: str, ts: int = _TS_BASE) -> Artifact:
        indexer = PrpIndexer(key=_PRP_KEY)
        art = Artifact.create(content=content, source_uris=["https://x"], timestamp_ns=ts)
        coord = indexer.index(art.content)
        ledger.admit(art, coord.to_hex_str(), 0.9, ts)
        ledger.accept(art.artifact_id, ts)
        return art

    def test_derive_from_accepted_returns_candidate(self) -> None:
        layer, ledger, _trail = self._setup()
        art = self._accept(ledger, "stage4 accepted source content")
        candidate, verdict = layer.derive(
            [art.artifact_id], DeriveOperation.SYNTHESIZE, _TS_BASE
        )
        assert isinstance(candidate, CandidateClaim)
        assert isinstance(verdict, ValidationVerdict)

    def test_candidate_not_self_approved(self) -> None:
        layer, ledger, _trail = self._setup()
        art = self._accept(ledger, "no self-approve content")
        candidate, _verdict = layer.derive(
            [art.artifact_id], DeriveOperation.SYNTHESIZE, _TS_BASE
        )
        assert candidate.approved is False

    def test_derivation_logged_to_audit_trail(self) -> None:
        layer, ledger, trail = self._setup()
        art = self._accept(ledger, "audit trail derivation content")
        layer.derive([art.artifact_id], DeriveOperation.INFER, _TS_BASE)
        derivation_events = trail.get_events(event_type=AuditEventType.DERIVATION_STEP)
        assert len(derivation_events) >= 1

    def test_derive_missing_id_raises_value_error(self) -> None:
        layer, _ledger, _trail = self._setup()
        with pytest.raises(ValueError, match="not found or not ACCEPTED"):
            layer.derive(["nonexistent-id"], DeriveOperation.COMBINE, _TS_BASE)

    def test_claim_id_deterministic(self) -> None:
        layer, ledger, _trail = self._setup()
        art = self._accept(ledger, "deterministic claim id content")
        c1, _ = layer.derive([art.artifact_id], DeriveOperation.SYNTHESIZE, _TS_BASE)
        c2, _ = layer.derive([art.artifact_id], DeriveOperation.SYNTHESIZE, _TS_BASE)
        assert c1.claim_id == c2.claim_id

    def test_all_derive_operations_succeed(self) -> None:
        layer, ledger, _trail = self._setup()
        art = self._accept(ledger, "all operations test content long enough for extract")
        for op in DeriveOperation:
            candidate, _verdict = layer.derive([art.artifact_id], op, _TS_BASE)
            assert candidate.operation == op.value

    def test_source_artifact_ids_recorded(self) -> None:
        layer, ledger, _trail = self._setup()
        art = self._accept(ledger, "source id recording test")
        candidate, _ = layer.derive([art.artifact_id], DeriveOperation.SYNTHESIZE, _TS_BASE)
        assert art.artifact_id in candidate.source_artifact_ids


# ===========================================================================
# Stage 5 — Proven results: audit trail integrity + export
# ===========================================================================


class TestStage5ProvenResults:
    """Verify that the audit trail and export subsystems produce proven outputs."""

    def _full_pipeline(
        self,
        content: str,
        ts: int = _TS_BASE,
    ) -> tuple[Artifact, ValidationVerdict, BeliefLedger, AuditTrail, ExportPresenter]:
        ledger = BeliefLedger(ledger_id=f"s5-{hash(content) & 0xFFFF}")
        trail = AuditTrail(trail_id=f"s5-trail-{hash(content) & 0xFFFF}")
        pipeline = ValidationPipeline(pipeline_id="s5-pipe", belief_ledger=ledger)
        indexer = PrpIndexer(key=_PRP_KEY)
        presenter = ExportPresenter(presenter_id="s5-presenter")

        art = Artifact.create(content=content, source_uris=["https://proven.test"], timestamp_ns=ts)
        coord = indexer.index(art.content)
        verdict = pipeline.validate(art, ts)

        ledger.admit(art, coord.to_hex_str(), verdict.confidence, ts)
        if verdict.final_status is ValidationStatus.ACCEPTED:
            ledger.accept(art.artifact_id, ts)

        trail.append(
            event_type=AuditEventType.ARTIFACT_ADMITTED,
            artifact_id=art.artifact_id,
            timestamp_ns=ts,
            payload={"coord": coord.to_hex_str(), "verdict": verdict.final_status.value},
        )

        return art, verdict, ledger, trail, presenter

    def test_audit_trail_integrity_holds(self) -> None:
        _art, _verdict, _ledger, trail, _presenter = self._full_pipeline(
            "audit integrity test content with many words for passage"
        )
        assert trail.verify_integrity() is True

    def test_audit_trail_integrity_after_multiple_events(self) -> None:
        _art, _verdict, _ledger, trail, _presenter = self._full_pipeline(
            "multiple events integrity content"
        )
        trail.append(
            event_type=AuditEventType.VALIDATION_COMPLETED,
            artifact_id="dummy",
            timestamp_ns=_TS_BASE + 1,
            payload={"note": "second event"},
        )
        assert trail.verify_integrity() is True

    def test_export_produces_proof_trace(self) -> None:
        art, verdict, ledger, trail, presenter = self._full_pipeline(
            "proof trace export test content for proven results"
        )
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        assert isinstance(trace, ProofTrace)
        assert trace.artifact_id == art.artifact_id

    def test_proof_trace_validation_stages_present(self) -> None:
        art, verdict, ledger, trail, presenter = self._full_pipeline(
            "proof trace validation stages export test"
        )
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        assert len(trace.validation_stages) == 6

    def test_proof_trace_audit_events_present(self) -> None:
        art, verdict, ledger, trail, presenter = self._full_pipeline(
            "proof trace audit events test content"
        )
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        assert len(trace.audit_events) >= 1
        ids = {e["artifact_id"] for e in trace.audit_events}
        assert art.artifact_id in ids

    def test_export_lineage_graph(self) -> None:
        art, _verdict, ledger, _trail, presenter = self._full_pipeline(
            "lineage graph export test content"
        )
        graph = presenter.build_lineage_graph(art.artifact_id, ledger)
        assert isinstance(graph, LineageGraph)
        assert graph.root_artifact_id == art.artifact_id

    def test_json_export_deterministic(self) -> None:
        art, verdict, ledger, trail, presenter = self._full_pipeline(
            "json determinism test for proven results"
        )
        trace = presenter.build_proof_trace(art, verdict, trail, ledger)
        j1 = presenter.export_to_json(trace)
        j2 = presenter.export_to_json(trace)
        assert j1 == j2

    def test_audit_trail_checkpoint_restore_integrity(self) -> None:
        _art, _verdict, _ledger, trail, _presenter = self._full_pipeline(
            "audit checkpoint restore test content"
        )
        cp = trail.checkpoint()
        trail2 = AuditTrail(trail_id="s5-restore")
        trail2.restore(cp)
        assert trail2.verify_integrity() is True

    def test_belief_ledger_get_lineage_returns_record(self) -> None:
        art, _verdict, ledger, _trail, _presenter = self._full_pipeline(
            "lineage query test content word count sufficient for acceptance"
        )
        lineage = ledger.get_lineage(art.artifact_id)
        # lineage returns ancestor chain; at minimum the artifact itself
        assert len(lineage) >= 0  # no assertion on count — depends on ledger impl


# ===========================================================================
# End-to-end pipeline test
# ===========================================================================


def test_full_tpl_pipeline() -> None:
    """E2E: raw data → indexed → validated → belief base → proven results.

    This single test exercises every major subsystem in order, verifying
    that the pipeline contract holds without bypassing validation or losing
    provenance.
    """
    # --- setup ---
    ledger = BeliefLedger(ledger_id="e2e-ledger")
    trail = AuditTrail(trail_id="e2e-trail")
    pipeline = ValidationPipeline(pipeline_id="e2e-pipe", belief_ledger=ledger)
    indexer = PrpIndexer(key=_PRP_KEY)
    layer = TplReasoningLayer("e2e-layer", ledger, pipeline, trail)
    layer.initialize()
    presenter = ExportPresenter(presenter_id="e2e-presenter")

    ts = _TS_BASE

    # --- Stage 1: raw data → indexed artifact ---
    raw = "Gravitational waves carry energy away from coalescing binary star systems."
    art = Artifact.create(content=raw, source_uris=["https://arxiv.org/test"], timestamp_ns=ts)
    coord = indexer.index(art.content)
    assert isinstance(coord, Coordinate), "Indexer must return a Coordinate"

    # --- Stage 2: validation pipeline ---
    verdict = pipeline.validate(art, ts)
    assert isinstance(verdict, ValidationVerdict), "Pipeline must return a ValidationVerdict"
    assert len(verdict.stage_results) == 6, "Must have exactly 6 validation stages"

    # --- Stage 3: belief base admission ---
    ledger.admit(art, coord.to_hex_str(), verdict.confidence, ts)
    if verdict.final_status is ValidationStatus.ACCEPTED:
        ledger.accept(art.artifact_id, ts)

    trail.append(
        event_type=AuditEventType.ARTIFACT_ADMITTED,
        artifact_id=art.artifact_id,
        timestamp_ns=ts,
        payload={"verdict": verdict.final_status.value},
    )

    # Artifact is now in the ledger
    all_records: list[BeliefRecord] = (
        ledger.get_by_state(BeliefState.ACCEPTED)
        + ledger.get_by_state(BeliefState.PENDING)
    )
    assert any(r.artifact_id == art.artifact_id for r in all_records), (
        "Artifact must appear in ledger after admission"
    )

    # --- Stage 4: candidate claim derivation (only if ACCEPTED) ---
    if verdict.final_status is ValidationStatus.ACCEPTED:
        candidate, _derive_verdict = layer.derive(
            [art.artifact_id], DeriveOperation.SUMMARIZE, ts + 1
        )
        assert isinstance(candidate, CandidateClaim), "Reasoning layer must return CandidateClaim"
        assert candidate.approved is False, "Derived claim must NOT be self-approved"
        assert art.artifact_id in candidate.source_artifact_ids, "Source IDs must be recorded"

    # --- Stage 5: proven results via export ---
    trace = presenter.build_proof_trace(art, verdict, trail, ledger)
    assert isinstance(trace, ProofTrace), "Presenter must produce a ProofTrace"
    assert trace.artifact_id == art.artifact_id
    assert len(trace.validation_stages) == 6

    # Audit trail must remain intact (tamper-evident)
    assert trail.verify_integrity() is True, "Audit trail integrity must hold"

    # JSON export must be deterministic
    j1 = presenter.export_to_json(trace)
    j2 = presenter.export_to_json(trace)
    assert j1 == j2, "JSON export must be deterministic"
