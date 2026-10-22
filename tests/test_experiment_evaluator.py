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
    primary_metric: str = "pass_rate",
) -> ExperimentSpec:
    """Create a fixed experiment spec for reproducible tests."""
    return ExperimentSpec(
        experiment_id="exp-repr-001",
        task_family="repository-fix",
        task_description="Fix a deterministic defect and run the regression suite",
        dataset_version="fixture-v1",
        baseline_candidate_id="baseline",
        primary_metric=primary_metric,
        metrics=[
            MetricDefinition(
                name="pass_rate",
                direction=direction if primary_metric == "pass_rate" else MetricDirection.MAXIMIZE,
                required=True,
                target_value=target if primary_metric == "pass_rate" else 0.8,
            ),
            MetricDefinition(
                name="cost_usd",
                direction=direction if primary_metric == "cost_usd" else MetricDirection.MINIMIZE,
                required=True,
                target_value=2.0,
            ),
        ],
        require_evidence=True,
        configuration_digest="a" * 64,
    )


def make_run(
    candidate_id: str,
    pass_rates: list[float],
    cost_samples: list[float],
    *,
    tests_passed: bool = True,
    evidence_refs: list[str] | None = None,
    representation_id: str = "graph-v1",
    environment_fingerprint: str = "env-python312-deps-v1",
    sample_ids: list[str] | None = None,
) -> CandidateRun:
    """Create a fixed candidate measurement."""
    return CandidateRun(
        run_id=f"run-{candidate_id}",
        candidate_id=candidate_id,
        approach="candidate approach",
        representation_id=representation_id,
        implementation_version="commit-abc123",
        environment_fingerprint=environment_fingerprint,
        model_versions={"solver": "test-double-1"},
        configuration_digest="b" * 64,
        metric_samples={"pass_rate": pass_rates, "cost_usd": cost_samples},
        sample_ids=sample_ids or [],
        tests_passed=tests_passed,
        test_ids=["unit-1", "integration-1"],
        evidence_refs=evidence_refs if evidence_refs is not None else ["artifact:run-1"],
        elapsed_ms=100.0,
        cost_usd=sum(cost_samples) / len(cost_samples),
    )


def test_ranks_only_eligible_candidates_by_primary_metric() -> None:
    spec = make_spec()
    baseline = make_run("baseline", [0.7, 0.7], [1.5, 1.5])
    better = make_run(
        "candidate-b", [0.94, 0.96], [1.8, 1.8], representation_id="constraint-v2"
    )
    cheaper = make_run("candidate-a", [0.84, 0.86], [0.9, 0.9], representation_id="graph-v2")
    report = ExperimentEvaluator.compare(spec, [baseline, cheaper, better])
    assert report.ranked_candidate_ids == ["candidate-b", "candidate-a"]
    assessments = {item.candidate_id: item for item in report.assessments}
    assert assessments["candidate-b"].primary_improvement == pytest.approx(0.25)
    assert assessments["candidate-b"].relative_primary_improvement_percent == pytest.approx(
        0.25 / 0.7 * 100.0
    )
    comparison = assessments["candidate-b"].metric_comparisons["pass_rate"]
    assert comparison.baseline_sample_count == 2
    assert comparison.candidate_sample_count == 2
    assert comparison.candidate_sample_stddev is not None


def test_minimizing_primary_metric_ranks_lower_values_first() -> None:
    spec = make_spec(
        direction=MetricDirection.MINIMIZE,
        target=2.0,
        primary_metric="cost_usd",
    )
    baseline = make_run("baseline", [0.9, 0.9], [1.8, 1.8])
    high_cost = make_run("high-cost", [0.95, 0.95], [1.7, 1.7])
    low_cost = make_run("low-cost", [0.90, 0.90], [1.0, 1.0])
    report = ExperimentEvaluator.compare(spec, [baseline, high_cost, low_cost])
    assert report.ranked_candidate_ids == ["low-cost", "high-cost"]
    assessments = {item.candidate_id: item for item in report.assessments}
    assert assessments["low-cost"].primary_improvement == pytest.approx(0.8)


def test_excludes_failed_tests_without_hiding_failure() -> None:
    report = ExperimentEvaluator.compare(
        make_spec(),
        [
            make_run("baseline", [0.7], [1.5]),
            make_run("broken", [0.99], [0.5], tests_passed=False),
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
            make_run("baseline", [0.7], [1.5]),
            make_run("untraceable", [0.9], [1.0], evidence_refs=[]),
        ],
    )
    candidate = next(item for item in report.assessments if item.candidate_id == "untraceable")
    assert not candidate.eligible
    assert "missing_evidence" in candidate.exclusion_reasons


def test_candidate_below_target_is_not_ranked() -> None:
    report = ExperimentEvaluator.compare(
        make_spec(),
        [
            make_run("baseline", [0.7], [1.5]),
            make_run("misses-target", [0.78, 0.8], [1.0, 1.0]),
        ],
    )
    candidate = next(item for item in report.assessments if item.candidate_id == "misses-target")
    assert not candidate.eligible
    assert "target_not_met:pass_rate" in candidate.exclusion_reasons


def test_report_digest_is_independent_of_input_order() -> None:
    spec = make_spec()
    baseline = make_run("baseline", [0.7, 0.7], [1.5, 1.5])
    candidate = make_run("candidate", [0.9, 0.9], [1.0, 1.0])
    first = ExperimentEvaluator.compare(spec, [baseline, candidate])
    second = ExperimentEvaluator.compare(spec, [candidate, baseline])
    assert first.report_digest == second.report_digest
    assert first.spec_digest == second.spec_digest


def test_missing_baseline_fails_fast() -> None:
    with pytest.raises(ValueError, match="baseline candidate is missing"):
        ExperimentEvaluator.compare(make_spec(), [make_run("other", [0.9], [1.0])])


def test_unknown_metrics_fail_instead_of_being_silently_ignored() -> None:
    spec = make_spec()
    baseline = make_run("baseline", [0.7], [1.5])
    invalid = make_run("candidate", [0.9], [1.0]).model_copy(
        update={
            "metric_samples": {
                "pass_rate": [0.9],
                "cost_usd": [1.0],
                "confidence_guess": [0.99],
            }
        }
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
        make_run("bad", [float("nan")], [1.0])


def test_candidate_and_baseline_must_share_execution_environment() -> None:
    with pytest.raises(ValueError, match="environment_fingerprint values must match"):
        ExperimentEvaluator.compare(
            make_spec(),
            [
                make_run("baseline", [0.7], [1.5]),
                make_run("candidate", [0.9], [1.0], environment_fingerprint="different-env"),
            ],
        )


def test_report_converts_to_pending_canonical_artifact() -> None:
    report = ExperimentEvaluator.compare(
        make_spec(),
        [
            make_run("baseline", [0.7], [1.5]),
            make_run(
                "candidate",
                [0.9],
                [1.0],
                evidence_refs=["artifact:evidence-2", "artifact:evidence-1"],
            ),
        ],
    )
    artifact = report_to_artifact(report, timestamp_ns=123456789)
    assert artifact.metadata["artifact_kind"] == "experiment_report"
    assert artifact.metadata["report_digest"] == report.report_digest
    assert artifact.timestamp_ns == 123456789
    assert artifact.source_uris == ["artifact:evidence-1", "artifact:evidence-2"]
    assert artifact.validation_status.value == "pending"


def test_report_artifact_identity_is_reproducible_for_fixed_timestamp() -> None:
    runs = [make_run("baseline", [0.7], [1.5]), make_run("candidate", [0.9], [1.0])]
    report = ExperimentEvaluator.compare(make_spec(), runs)
    first = report_to_artifact(report, timestamp_ns=10)
    second = report_to_artifact(report, timestamp_ns=10)
    assert first.artifact_id == second.artifact_id
    assert first.content_hash == second.content_hash



def test_directive_reference_requires_id_and_digest_together() -> None:
    base = make_spec().model_dump(mode="python")
    base["directive_id"] = "hdr-123"
    with pytest.raises(ValidationError, match="must be supplied together"):
        ExperimentSpec.model_validate(base)


def test_directive_digest_must_be_sha256_hex() -> None:
    base = make_spec().model_dump(mode="python")
    base["directive_id"] = "hdr-123"
    base["directive_digest"] = "not-a-digest"
    with pytest.raises(ValidationError, match="lowercase SHA-256 hex digest"):
        ExperimentSpec.model_validate(base)


def test_report_artifact_preserves_directive_lineage() -> None:
    base = make_spec().model_dump(mode="python")
    base["directive_id"] = "hdr-123"
    base["directive_digest"] = "c" * 64
    spec = ExperimentSpec.model_validate(base)
    report = ExperimentEvaluator.compare(
        spec,
        [
            make_run("baseline", [0.7], [1.5]),
            make_run("candidate", [0.9], [1.0]),
        ],
    )
    artifact = report_to_artifact(report, timestamp_ns=10)
    assert "directive:hdr-123" in artifact.source_uris


def test_report_verification_detects_nested_content_mutation() -> None:
    """Report digests can be recomputed after serialization and detect tampering."""
    report = ExperimentEvaluator.compare(
        make_spec(),
        [
            make_run("baseline", [0.7, 0.7], [1.5, 1.5]),
            make_run("candidate", [0.9, 0.9], [1.0, 1.0]),
        ],
    )
    assert ExperimentEvaluator.verify_report(report)
    candidate = next(item for item in report.assessments if item.candidate_id == "candidate")
    candidate.metric_samples["pass_rate"].append(0.1)
    assert not ExperimentEvaluator.verify_report(report)


def test_report_verification_fails_when_spec_is_modified() -> None:
    """The spec digest binds the report to its task definition."""
    report = ExperimentEvaluator.compare(
        make_spec(),
        [
            make_run("baseline", [0.7], [1.5]),
            make_run("candidate", [0.9], [1.0]),
        ],
    )
    report.spec.metrics[0] = MetricDefinition(
        name="mutated-metric", direction=MetricDirection.MAXIMIZE
    )
    assert not ExperimentEvaluator.verify_report(report)


def test_paired_improvements_align_cases_by_id_not_list_order() -> None:
    """Per-case effect statistics align candidates even when sample order differs."""
    spec = make_spec()
    baseline = make_run(
        "baseline",
        [0.7, 0.9],
        [1.5, 1.6],
        sample_ids=["case-a", "case-b"],
    )
    candidate = make_run(
        "candidate",
        [0.8, 0.8],
        [1.6, 1.5],
        sample_ids=["case-b", "case-a"],
    )
    report = ExperimentEvaluator.compare(spec, [baseline, candidate])
    assessment = next(item for item in report.assessments if item.candidate_id == "candidate")
    comparison = assessment.metric_comparisons["pass_rate"]
    assert comparison.baseline_value == pytest.approx(0.8)
    assert comparison.candidate_value == pytest.approx(0.8)
    assert comparison.paired_sample_count == 2
    assert comparison.paired_improvement_mean == pytest.approx(0.0)
    assert comparison.paired_improvement_stddev == pytest.approx(0.1414213562)


def test_paired_candidate_must_use_same_case_set_as_baseline() -> None:
    """An unaligned task set must not be presented as a paired comparison."""
    with pytest.raises(ValueError, match="same task/trial set"):
        ExperimentEvaluator.compare(
            make_spec(),
            [
                make_run("baseline", [0.7, 0.9], [1.5, 1.6], sample_ids=["case-a", "case-b"]),
                make_run("candidate", [0.8, 0.8], [1.0, 1.0], sample_ids=["case-a", "case-c"]),
            ],
        )


def test_sample_id_count_must_match_each_metric_vector() -> None:
    """Paired statistics require exactly one measurement per declared sample ID."""
    with pytest.raises(ValidationError, match="sample_ids length must match"):
        CandidateRun(
            run_id="bad-sample-count",
            candidate_id="bad",
            approach="test",
            representation_id="graph",
            implementation_version="abc",
            environment_fingerprint="env-v1",
            metric_samples={"pass_rate": [0.8, 0.9]},
            sample_ids=["case-a"],
            tests_passed=True,
            elapsed_ms=1.0,
        )
