"""Deterministic evaluation of recorded candidate results against a baseline.

The evaluator performs no candidate execution. Callers run candidates in a
separately controlled test harness and pass the resulting measurements here.
"""

from __future__ import annotations

import hashlib
import json
from math import sqrt

from thalos_prime.experiments.contracts import (
    CandidateAssessment,
    CandidateRun,
    ExperimentReport,
    ExperimentSpec,
    MetricComparison,
    MetricDefinition,
    MetricDirection,
)


def _canonical_digest(value: object) -> str:
    """Hash a JSON-compatible value using stable serialization."""
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mean(samples: list[float]) -> float:
    """Return the arithmetic mean of a non-empty sample list."""
    return sum(samples) / len(samples)


def _sample_stddev(samples: list[float]) -> float | None:
    """Return sample standard deviation, or None when there is one observation."""
    if len(samples) < 2:
        return None
    average = _mean(samples)
    variance = sum((value - average) ** 2 for value in samples) / (len(samples) - 1)
    return sqrt(variance)


def _meets_target(value: float, metric: MetricDefinition) -> bool | None:
    """Return whether a measurement meets a configured target."""
    if metric.target_value is None:
        return None
    if metric.direction is MetricDirection.MAXIMIZE:
        return value >= metric.target_value
    return value <= metric.target_value


def _compare_metric(
    baseline_samples: list[float],
    candidate_samples: list[float],
    metric: MetricDefinition,
    paired_improvement_samples: list[float] | None = None,
) -> MetricComparison:
    """Compare sample means while preserving sample counts and dispersion."""
    baseline_value = _mean(baseline_samples)
    candidate_value = _mean(candidate_samples)
    absolute_delta = candidate_value - baseline_value
    directed_improvement = (
        absolute_delta
        if metric.direction is MetricDirection.MAXIMIZE
        else -absolute_delta
    )
    relative_improvement = (
        directed_improvement / abs(baseline_value) * 100.0
        if baseline_value != 0.0
        else None
    )
    return MetricComparison(
        baseline_value=baseline_value,
        candidate_value=candidate_value,
        absolute_delta=absolute_delta,
        directed_improvement=directed_improvement,
        relative_improvement_percent=relative_improvement,
        improved=directed_improvement > 0.0,
        meets_target=_meets_target(candidate_value, metric),
        baseline_sample_count=len(baseline_samples),
        candidate_sample_count=len(candidate_samples),
        baseline_sample_stddev=_sample_stddev(baseline_samples),
        candidate_sample_stddev=_sample_stddev(candidate_samples),
        paired_sample_count=len(paired_improvement_samples or []),
        paired_improvement_mean=(
            _mean(paired_improvement_samples)
            if paired_improvement_samples
            else None
        ),
        paired_improvement_stddev=(
            _sample_stddev(paired_improvement_samples)
            if paired_improvement_samples
            else None
        ),
    )


def _assessment(
    spec: ExperimentSpec,
    run: CandidateRun,
    baseline: CandidateRun,
    definitions: dict[str, MetricDefinition],
) -> CandidateAssessment:
    """Build a result assessment without running any untrusted code."""
    reasons: list[str] = []
    if not run.tests_passed:
        reasons.append("tests_failed")
    if spec.require_evidence and not run.evidence_refs:
        reasons.append("missing_evidence")
    for name, definition in definitions.items():
        if definition.required and name not in run.metric_samples:
            reasons.append(f"missing_required_metric:{name}")
    comparisons: dict[str, MetricComparison] = {}
    for name, samples in run.metric_samples.items():
        if name in definitions and name in baseline.metric_samples:
            paired_improvements: list[float] | None = None
            if baseline.sample_ids:
                baseline_by_sample = dict(
                    zip(
                        baseline.sample_ids,
                        baseline.metric_samples[name],
                        strict=True,
                    )
                )
                candidate_by_sample = dict(
                    zip(run.sample_ids, samples, strict=True)
                )
                metric = definitions[name]
                paired_improvements = [
                    (
                        candidate_by_sample[sample_id] - baseline_by_sample[sample_id]
                        if metric.direction is MetricDirection.MAXIMIZE
                        else baseline_by_sample[sample_id] - candidate_by_sample[sample_id]
                    )
                    for sample_id in sorted(baseline_by_sample)
                ]
            comparisons[name] = _compare_metric(
                baseline.metric_samples[name],
                samples,
                definitions[name],
                paired_improvement_samples=paired_improvements,
            )
    for name, samples in run.metric_samples.items():
        if name in definitions:
            target_met = _meets_target(_mean(samples), definitions[name])
            if target_met is False:
                reasons.append(f"target_not_met:{name}")
    primary_samples = run.metric_samples.get(spec.primary_metric)
    primary_comparison = comparisons.get(spec.primary_metric)
    return CandidateAssessment(
        run_id=run.run_id,
        candidate_id=run.candidate_id,
        approach=run.approach,
        representation_id=run.representation_id,
        implementation_version=run.implementation_version,
        environment_fingerprint=run.environment_fingerprint,
        model_versions=run.model_versions,
        configuration_digest=run.configuration_digest,
        eligible=not reasons,
        exclusion_reasons=sorted(set(reasons)),
        primary_metric_value=_mean(primary_samples) if primary_samples else None,
        primary_improvement=(
            primary_comparison.directed_improvement
            if primary_comparison is not None
            else None
        ),
        relative_primary_improvement_percent=(
            primary_comparison.relative_improvement_percent
            if primary_comparison is not None
            else None
        ),
        metric_samples=run.metric_samples,
        sample_ids=run.sample_ids,
        metric_comparisons=comparisons,
        tests_passed=run.tests_passed,
        test_ids=sorted(set(run.test_ids)),
        evidence_refs=sorted(set(run.evidence_refs)),
        elapsed_ms=run.elapsed_ms,
        cost_usd=run.cost_usd,
        failure_summary=run.failure_summary,
    )


class ExperimentEvaluator:
    """Compare pre-recorded candidate measurements against a defined baseline."""

    @staticmethod
    def compare(spec: ExperimentSpec, runs: list[CandidateRun]) -> ExperimentReport:
        """Validate and compare a batch of runs using a preregistered spec.

        Candidate execution belongs outside this method. Each run is a record
        of results produced elsewhere, such as unit tests, a benchmark, a
        simulation, or a controlled experiment.
        """
        if not runs:
            raise ValueError("at least one candidate run, including the baseline, is required")
        identifiers = [run.candidate_id for run in runs]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("candidate_id values must be unique within an experiment")
        run_ids = [run.run_id for run in runs]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("run_id values must be unique within an experiment")
        by_id = {run.candidate_id: run for run in runs}
        if spec.baseline_candidate_id not in by_id:
            raise ValueError("the declared baseline candidate is missing")
        definitions = {metric.name: metric for metric in spec.metrics}
        for run in runs:
            unknown_metrics = sorted(set(run.metric_samples) - set(definitions))
            if unknown_metrics:
                raise ValueError(
                    f"candidate {run.candidate_id!r} has undeclared metrics: "
                    + ", ".join(unknown_metrics)
                )
        baseline = by_id[spec.baseline_candidate_id]
        if not baseline.tests_passed:
            raise ValueError("baseline tests must pass before candidate comparison")
        if spec.require_evidence and not baseline.evidence_refs:
            raise ValueError("baseline evidence is required by the experiment spec")
        missing_baseline = [
            name for name, definition in definitions.items()
            if definition.required and name not in baseline.metric_samples
        ]
        if missing_baseline:
            raise ValueError(
                "baseline is missing required metrics: " + ", ".join(sorted(missing_baseline))
            )
        for run in runs:
            if run.environment_fingerprint != baseline.environment_fingerprint:
                raise ValueError(
                    "candidate and baseline environment_fingerprint values must match"
                )
            if bool(run.sample_ids) != bool(baseline.sample_ids):
                raise ValueError(
                    "candidate and baseline must both specify sample_ids or leave them both empty"
                )
            if baseline.sample_ids and set(run.sample_ids) != set(baseline.sample_ids):
                raise ValueError(
                    "candidate and baseline sample_ids must identify the same task/trial set"
                )
        assessments = [
            _assessment(spec, run, baseline, definitions)
            for run in sorted(runs, key=lambda item: item.candidate_id)
        ]
        eligible_candidates = [
            assessment for assessment in assessments
            if assessment.eligible and assessment.candidate_id != spec.baseline_candidate_id
        ]
        primary_direction = definitions[spec.primary_metric].direction
        if primary_direction is MetricDirection.MAXIMIZE:
            eligible_candidates.sort(
                key=lambda item: (
                    -(item.primary_metric_value if item.primary_metric_value is not None else 0.0),
                    item.cost_usd,
                    item.elapsed_ms,
                    item.candidate_id,
                )
            )
        else:
            eligible_candidates.sort(
                key=lambda item: (
                    (
                        item.primary_metric_value
                        if item.primary_metric_value is not None
                        else float("inf")
                    ),
                    item.cost_usd,
                    item.elapsed_ms,
                    item.candidate_id,
                )
            )
        spec_payload = spec.model_dump(mode="json")
        spec_digest = _canonical_digest(spec_payload)
        report_body = {
            "experiment_id": spec.experiment_id,
            "task_family": spec.task_family,
            "baseline_candidate_id": spec.baseline_candidate_id,
            "primary_metric": spec.primary_metric,
            "spec": spec_payload,
            "spec_digest": spec_digest,
            "assessments": [item.model_dump(mode="json") for item in assessments],
            "ranked_candidate_ids": [item.candidate_id for item in eligible_candidates],
        }
        report_digest = _canonical_digest(report_body)
        return ExperimentReport(**report_body, report_digest=report_digest)

    @staticmethod
    def verify_report(report: ExperimentReport) -> bool:
        """Verify report/spec digests against the report's current serialized contents.

        This detects accidental or deliberate content changes when a trusted
        digest is available. It does not authenticate who created the report.
        """
        try:
            spec_payload = report.spec.model_dump(mode="json")
            if _canonical_digest(spec_payload) != report.spec_digest:
                return False
            report_body = {
                "experiment_id": report.experiment_id,
                "task_family": report.task_family,
                "baseline_candidate_id": report.baseline_candidate_id,
                "primary_metric": report.primary_metric,
                "spec": spec_payload,
                "spec_digest": report.spec_digest,
                "assessments": [
                    item.model_dump(mode="json") for item in report.assessments
                ],
                "ranked_candidate_ids": report.ranked_candidate_ids,
            }
            return _canonical_digest(report_body) == report.report_digest
        except (TypeError, ValueError):
            return False


__all__ = ["ExperimentEvaluator"]
