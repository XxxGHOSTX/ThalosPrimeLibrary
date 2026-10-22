"""Tests for reproducible, evidence-gated candidate evaluation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from thalos_prime.experiments import (
    CandidateRun,
    ExperimentEvaluator,
    ExperimentSpec,
    MetricDefinition,
    MetricDirection,
    report_to_artifact,
)


def make_spec(
    direction: MetricDirection = MetricDirection.MAXIMIZE,
    target: float | None = 0.8,
) -> ExperimentSpec:
    """Create a fixed experiment spec for reproducible tests."""
    return ExperimentSpec(
        experiment_id="exp-repr-001",
        task_family="repository-fix",
        task_description="Fix a deterministic defect and run the regression suite",
        dataset_version="fixture-v1",
        baseline_candidate_id="baseline",
        primary_metric="pass_rate",
        metrics=[
            MetricDefinition(
                name="pass_rate",
                direction=direction,
                required=True,
                target_value=target,
            ),
            MetricDefinition(
                name="cost_usd",
                direction=MetricDirection.MINIMIZE,
                required=True,
                target_value=2.0,
            ),
        ],
        require_evidence=True,
        configuration_digest="a" * 64,
    )


def make_run(
    candidate_id: str,
    pass_rate: float,
    cost_usd: float,
    *,
    tests_passed: bool = True,
    evidence_refs: list[str] | None = None,
    representation_id: str = "graph-v1",
) -> CandidateRun:
    """Create a fixed candidate measurement."""
    return CandidateRun(
        candidate_id=candidate_id,
        approach="candidate approach",
        representation_id=representation_id,
        implementation_version="commit-abc123",
        metrics={"pass_rate": pass_rate, "cost_usd": cost_usd},
        tests_passed=tests_passed,
        test_ids=["unit-1", "integration-1"],
        evidence_refs=evidence_refs if evidence_refs is not None else ["artifact:run-1"],
        elapsed_ms=100.0,
        cost_usd=cost_usd,
    )


def test_ranks_only_eligible_candidates_by_primary_metric() -> None:
    spec = make_spec()
    baseline = make_run("baseline", 0.7, 1.5)
    better = make_run("candidate-b", 0.95, 1.8, representation_id="constraint-v2")
    cheaper = make_run("candidate-a", 0.85, 0.9, representation_id="graph-v2")
    report = ExperimentEvaluator.compare(spec, [baseline, cheaper, better])
    assert report.ranked_candidate_ids == ["candidate-b", "candidate-a"]
    assessments = {item.candidate_id: item for item in report.assessments}
    assert assessments["candidate-b"].primary_improvement == pytest.approx(0.25)
    assert assessments["candidate-b"].relative_primary_improvement_percent == pytest.approx(
        0.25 / 0.7 * 100.0
    )


def test_minimizing_primary_metric_ranks_lower_values_first() -> None:
    spec = make_spec(direction=MetricDirection.MINIMIZE, target=0.8).model_copy(
        update={
            "primary_metric": "cost_usd",
            "metrics": [
                MetricDefinition(
                    name="pass_rate",
                    direction=MetricDirection.MAXIMIZE,
                    required=True,
                    target_value=0.8,
                ),
                MetricDefinition(
                    name="cost_usd",
                    direction=MetricDirection.MINIMIZE,
                    required=True,
                    target_value=2.0,
                ),
            ],
        }
    )
    baseline = make_run("baseline", 0.9, 1.8)
    high_cost = make_run("high-cost", 0.95, 1.7)
    low_cost = make_run("low-cost", 0.90, 1.0)
    report = ExperimentEvaluator.compare(spec, [baseline, high_cost, low_cost])
    assert report.ranked_candidate_ids == ["low-cost", "high-cost"]
    assessments = {item.candidate_id: item for item in report.assessments}
    assert assessments["low-cost"].primary_improvement == pytest.approx(0.8)


def test_excludes_failed_tests_without_hiding_failure() -> None:
    report = ExperimentEvaluator.compare(
        make_spec(),
        [
            make_run("baseline", 0.7, 1.5),
            make_run("broken", 0.99, 0.5, tests_passed=False),
        ],
    )
    assert report.ranked_candidate_ids == []
    broken = next(item for item in report.assessments if item.candidate_id == "broken")
    assert not broken.eligible
    assert "tests_failed" in broken.exclusion_reasons


def test_evidence_is_required_when_spec_says_so() -> None:
    report = ExperimentEvaluator.compare(
        make_spec(),
        [
            make_run("baseline", 0.7, 1.5),
            make_run("untraceable", 0.9, 1.0, evidence_refs=[]),
        ],
    )
    candidate = next(item for item in report.assessments if item.candidate_id == "untraceable")
    assert not candidate.eligible
    assert "missing_evidence" in candidate.exclusion_reasons


def test_candidate_below_target_is_not_ranked() -> None:
    report = ExperimentEvaluator.compare(
        make_spec(),
        [
            make_run("baseline", 0.7, 1.5),
            make_run("misses-target", 0.79, 1.0),
        ],
    )
    candidate = next(item for item in report.assessments if item.candidate_id == "misses-target")
    assert not candidate.eligible
    assert "target_not_met:pass_rate" in candidate.exclusion_reasons


def test_report_digest_is_independent_of_input_order() -> None:
    spec = make_spec()
    baseline = make_run("baseline", 0.7, 1.5)
    candidate = make_run("candidate", 0.9, 1.0)
    first = ExperimentEvaluator.compare(spec, [baseline, candidate])
    second = ExperimentEvaluator.compare(spec, [candidate, baseline])
    assert first.report_digest == second.report_digest
    assert first.spec_digest == second.spec_digest


def test_missing_baseline_fails_fast() -> None:
    with pytest.raises(ValueError, match="baseline candidate is missing"):
        ExperimentEvaluator.compare(make_spec(), [make_run("other", 0.9, 1.0)])


def test_unknown_metrics_fail_instead_of_being_silently_ignored() -> None:
    spec = make_spec()
    baseline = make_run("baseline", 0.7, 1.5)
    invalid = make_run("candidate", 0.9, 1.0).model_copy(
        update={"metrics": {"pass_rate": 0.9, "cost_usd": 1.0, "confidence_guess": 0.99}}
    )
    with pytest.raises(ValueError, match="undeclared metrics"):
        ExperimentEvaluator.compare(spec, [baseline, invalid])


def test_duplicate_metric_names_are_rejected() -> None:
    base = make_spec().model_dump(mode="python")
    base["metrics"] = [
        MetricDefinition(name="pass_rate", direction=MetricDirection.MAXIMIZE),
        MetricDefinition(name="pass_rate", direction=MetricDirection.MINIMIZE),
    ]
    with pytest.raises(ValidationError, match="metric names must be unique"):
        ExperimentSpec.model_validate(base)


def test_nonfinite_measurements_are_rejected() -> None:
    with pytest.raises(ValidationError):
        make_run("bad", float("nan"), 1.0)



def test_report_converts_to_pending_canonical_artifact() -> None:
    report = ExperimentEvaluator.compare(
        make_spec(),
        [
            make_run("baseline", 0.7, 1.5),
            make_run("candidate", 0.9, 1.0, evidence_refs=["artifact:evidence-2", "artifact:evidence-1"]),
        ],
    )
    artifact = report_to_artifact(report, timestamp_ns=123456789)
    assert artifact.metadata["artifact_kind"] == "experiment_report"
    assert artifact.metadata["report_digest"] == report.report_digest
    assert artifact.timestamp_ns == 123456789
    assert artifact.source_uris == ["artifact:evidence-1", "artifact:evidence-2"]
    assert artifact.validation_status.value == "pending"


def test_report_artifact_identity_is_reproducible_for_fixed_timestamp() -> None:
    runs = [make_run("baseline", 0.7, 1.5), make_run("candidate", 0.9, 1.0)]
    report = ExperimentEvaluator.compare(make_spec(), runs)
    first = report_to_artifact(report, timestamp_ns=10)
    second = report_to_artifact(report, timestamp_ns=10)
    assert first.artifact_id == second.artifact_id
    assert first.content_hash == second.content_hash
