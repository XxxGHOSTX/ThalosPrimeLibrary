"""Tests for the six-stage ValidationPipeline subsystem.

Covers ValidationStage, StageResult, ValidationVerdict, and ValidationPipeline
including happy path, stage scoring, contradiction search, and lifecycle methods.
All tests use deterministic inputs and fixed timestamps.
"""

from __future__ import annotations

from thalos_prime.artifacts.schema import Artifact, ValidationStatus
from thalos_prime.belief.ledger import BeliefLedger
from thalos_prime.validation.pipeline import (
    StageResult,
    ValidationPipeline,
    ValidationStage,
)

# ---------------------------------------------------------------------------
# Fixed test constants
# ---------------------------------------------------------------------------
_TS = 1_700_000_000_000_000_000  # Fixed nanosecond timestamp
_COORD = "0001020300040005"


def _make_artifact(
    content: str = "This is a valid content string for testing purposes",
    source_uris: list[str] | None = None,
    confidence: float = 0.8,
    ts: int = _TS,
) -> Artifact:
    uris = source_uris if source_uris is not None else ["uri://test-source"]
    art = Artifact.create(content=content, source_uris=uris, timestamp_ns=ts)
    return art.model_copy(update={"confidence": confidence})


def _make_pipeline(ledger_id: str = "ledger-001") -> tuple[ValidationPipeline, BeliefLedger]:
    ledger = BeliefLedger(ledger_id=ledger_id)
    ledger.initialize()
    pipeline = ValidationPipeline(pipeline_id="pipe-001", belief_ledger=ledger)
    return pipeline, ledger


# ===========================================================================
# ValidationStage
# ===========================================================================


class TestValidationStage:
    def test_all_members_present(self) -> None:
        members = set(ValidationStage)
        assert ValidationStage.CANONICALIZATION in members
        assert ValidationStage.SOURCE_BINDING in members
        assert ValidationStage.CONSISTENCY_ANALYSIS in members
        assert ValidationStage.CONTRADICTION_SEARCH in members
        assert ValidationStage.CONFIDENCE_ASSIGNMENT in members
        assert ValidationStage.ADMISSION_CONTROL in members

    def test_is_str(self) -> None:
        assert isinstance(ValidationStage.CANONICALIZATION, str)

    def test_values(self) -> None:
        assert ValidationStage.CANONICALIZATION.value == "canonicalization"
        assert ValidationStage.ADMISSION_CONTROL.value == "admission_control"


# ===========================================================================
# StageResult
# ===========================================================================


class TestStageResult:
    def test_fields_round_trip(self) -> None:
        result = StageResult(
            stage=ValidationStage.SOURCE_BINDING,
            passed=True,
            score=0.75,
            notes=["source_uri count: 3"],
            timestamp_ns=_TS,
        )
        assert result.stage is ValidationStage.SOURCE_BINDING
        assert result.passed is True
        assert result.score == 0.75
        assert result.notes == ["source_uri count: 3"]
        assert result.timestamp_ns == _TS

    def test_score_bounds(self) -> None:
        result = StageResult(
            stage=ValidationStage.CANONICALIZATION,
            passed=True,
            score=0.0,
            notes=[],
            timestamp_ns=_TS,
        )
        assert 0.0 <= result.score <= 1.0

    def test_serialisation_round_trip(self) -> None:
        result = StageResult(
            stage=ValidationStage.CONSISTENCY_ANALYSIS,
            passed=False,
            score=0.0,
            notes=["content too short"],
            timestamp_ns=_TS,
        )
        data = result.model_dump()
        restored = StageResult.model_validate(data)
        assert restored == result


# ===========================================================================
# ValidationVerdict
# ===========================================================================


class TestValidationVerdict:
    def test_schema_version_default(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        verdict = pipeline.validate(artifact, _TS)
        assert verdict.schema_version == 1

    def test_verdict_has_six_stages(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        verdict = pipeline.validate(artifact, _TS)
        assert len(verdict.stage_results) == 6

    def test_stage_order(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        verdict = pipeline.validate(artifact, _TS)
        expected_stages = [
            ValidationStage.CANONICALIZATION,
            ValidationStage.SOURCE_BINDING,
            ValidationStage.CONSISTENCY_ANALYSIS,
            ValidationStage.CONTRADICTION_SEARCH,
            ValidationStage.CONFIDENCE_ASSIGNMENT,
            ValidationStage.ADMISSION_CONTROL,
        ]
        for result, expected in zip(verdict.stage_results, expected_stages, strict=False):
            assert result.stage is expected

    def test_artifact_id_propagated(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        verdict = pipeline.validate(artifact, _TS)
        assert verdict.artifact_id == artifact.artifact_id

    def test_timestamp_propagated(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        verdict = pipeline.validate(artifact, _TS)
        assert verdict.timestamp_ns == _TS


# ===========================================================================
# ValidationPipeline - stage logic
# ===========================================================================


class TestValidationPipelineStages:
    def test_canonicalization_always_passes(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        verdict = pipeline.validate(artifact, _TS)
        r = verdict.stage_results[0]
        assert r.stage is ValidationStage.CANONICALIZATION
        assert r.passed is True
        assert r.score == 1.0

    def test_canonicalization_notes_include_length(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        verdict = pipeline.validate(artifact, _TS)
        r = verdict.stage_results[0]
        assert any("canonical_form length" in note for note in r.notes)

    def test_source_binding_fails_with_no_uris(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact(source_uris=[])
        verdict = pipeline.validate(artifact, _TS)
        r = verdict.stage_results[1]
        assert r.stage is ValidationStage.SOURCE_BINDING
        assert r.passed is False
        assert r.score == 0.0

    def test_source_binding_score_scales(self) -> None:
        pipeline, _ = _make_pipeline()
        art2 = _make_artifact(source_uris=["uri://a", "uri://b"])
        art4 = _make_artifact(source_uris=["uri://a", "uri://b", "uri://c", "uri://d"])
        v2 = pipeline.validate(art2, _TS)
        v4 = pipeline.validate(art4, _TS)
        s2 = v2.stage_results[1].score
        s4 = v4.stage_results[1].score
        assert s2 == 0.5
        assert s4 == 1.0

    def test_consistency_fails_short_content(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact(content="hi")
        verdict = pipeline.validate(artifact, _TS)
        r = verdict.stage_results[2]
        assert r.stage is ValidationStage.CONSISTENCY_ANALYSIS
        assert r.passed is False
        assert r.score == 0.0

    def test_consistency_passes_valid_content(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        verdict = pipeline.validate(artifact, _TS)
        r = verdict.stage_results[2]
        assert r.passed is True
        assert r.score == 1.0

    def test_contradiction_no_conflict_empty_ledger(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        verdict = pipeline.validate(artifact, _TS)
        r = verdict.stage_results[3]
        assert r.stage is ValidationStage.CONTRADICTION_SEARCH
        assert r.score == 1.0

    def test_confidence_score_in_range(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        verdict = pipeline.validate(artifact, _TS)
        r = verdict.stage_results[4]
        assert r.stage is ValidationStage.CONFIDENCE_ASSIGNMENT
        assert 0.0 <= r.score <= 1.0

    def test_admission_accepted_high_confidence(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact(confidence=1.0)
        verdict = pipeline.validate(artifact, _TS)
        r = verdict.stage_results[5]
        assert r.stage is ValidationStage.ADMISSION_CONTROL
        assert r.score == 1.0

    def test_admission_rejected_low_confidence(self) -> None:
        pipeline, _ = _make_pipeline()
        # Force very low scores: empty source URIs + short content
        artifact = _make_artifact(
            content="hi",
            source_uris=[],
            confidence=0.0,
        )
        verdict = pipeline.validate(artifact, _TS)
        r = verdict.stage_results[5]
        assert r.stage is ValidationStage.ADMISSION_CONTROL
        assert r.score == 0.0


# ===========================================================================
# ValidationPipeline - verdict status
# ===========================================================================


class TestValidationPipelineVerdict:
    def test_accepted_verdict(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact(confidence=1.0)
        verdict = pipeline.validate(artifact, _TS)
        assert verdict.final_status is ValidationStatus.ACCEPTED

    def test_rejected_verdict_no_sources_short_content(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact(content="hi", source_uris=[], confidence=0.0)
        verdict = pipeline.validate(artifact, _TS)
        assert verdict.final_status is ValidationStatus.REJECTED

    def test_facs_bundle_rejected_flag(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact(content="hi", source_uris=[], confidence=0.0)
        verdict = pipeline.validate(artifact, _TS)
        assert verdict.facs_bundle.flags.get("rejected") is True
        assert verdict.facs_bundle.flags.get("admitted") is False

    def test_facs_bundle_admitted_flag(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact(confidence=1.0)
        verdict = pipeline.validate(artifact, _TS)
        assert verdict.facs_bundle.flags.get("admitted") is True
        assert verdict.facs_bundle.flags.get("rejected") is False

    def test_determinism_same_inputs_same_outputs(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        v1 = pipeline.validate(artifact, _TS)
        v2 = pipeline.validate(artifact, _TS)
        assert v1.model_dump() == v2.model_dump()

    def test_operate_alias(self) -> None:
        pipeline, _ = _make_pipeline()
        artifact = _make_artifact()
        v1 = pipeline.validate(artifact, _TS)
        v2 = pipeline.operate(artifact, _TS)
        assert v1.model_dump() == v2.model_dump()


# ===========================================================================
# ValidationPipeline - lifecycle
# ===========================================================================


class TestValidationPipelineLifecycle:
    def test_pipeline_id(self) -> None:
        pipeline, _ = _make_pipeline()
        assert pipeline.pipeline_id == "pipe-001"

    def test_initialize(self) -> None:
        pipeline, _ = _make_pipeline()
        pipeline.initialize()  # Should not raise

    def test_reconcile(self) -> None:
        pipeline, _ = _make_pipeline()
        pipeline.reconcile()  # Should not raise

    def test_terminate(self) -> None:
        pipeline, _ = _make_pipeline()
        pipeline.terminate()  # Should not raise

    def test_checkpoint_contains_pipeline_id(self) -> None:
        pipeline, _ = _make_pipeline()
        data = pipeline.checkpoint()
        assert data["pipeline_id"] == "pipe-001"
        assert data["schema_version"] == 1

    def test_schema_version_class_attr(self) -> None:
        assert ValidationPipeline.schema_version == 1
