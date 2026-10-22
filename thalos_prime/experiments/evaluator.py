"""Deterministic evaluation of recorded candidate results against a baseline.

The evaluator performs no candidate execution. Callers run candidates in a
separately controlled test harness and pass the resulting measurements here.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from thalos_prime.experiments.contracts import (
    CandidateAssessment,
    CandidateRun,
    ExperimentReport,
    ExperimentSpec,
    MetricComparison,
    MetricDefinition,
    MetricDirection,
)


def _canonical_digest(value: Any) -> str:
    """Hash a JSON-compatible value using stable serialization."""
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _meets_target(value: float, metric: MetricDefinition) -> bool | None:
    """Return whether a measurement meets a configured target."""
    if metric.target_value is None:
        return None
    if metric.direction is MetricDirection.MAXIMIZE:
        return value >= metric.target_value
    return value <= metric.target_value


def _compare_metric(
    baseline_value: float,
    candidate_value: float,
    metric: MetricDefinition,
) -> MetricComparison:
    """Compute changes with positive directed change meaning improvement."""
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
        if definition.required and name not in run.metrics:
            reasons.append(f"missing_required_metric:{name}")
    comparisons: dict[str, MetricComparison] = {}
    for name, value in run.metrics.items():
        if name in definitions and name in baseline.metrics:
            comparisons[name] = _compare_metric(
                baseline.metrics[name],
                value,
                definitions[name],
            )
    for name, value in run.metrics.items():
        if name in definitions:
            target_met = _meets_target(value, definitions[name])
            if target_met is False:
                reasons.append(f"target_not_met:{name}")
    primary_value = run.metrics.get(spec.primary_metric)
    primary_comparison = comparisons.get(spec.primary_metric)
    return CandidateAssessment(
        candidate_id=run.candidate_id,
        approach=run.approach,
        representation_id=run.representation_id,
        implementation_version=run.implementation_version,
        eligible=not reasons,
        exclusion_reasons=sorted(set(reasons)),
        primary_metric_value=primary_value,
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
        metric_comparisons=comparisons,
        tests_passed=run.tests_passed,
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
        by_id = {run.candidate_id: run for run in runs}
        if spec.baseline_candidate_id not in by_id:
            raise ValueError("the declared baseline candidate is missing")
        definitions = {metric.name: metric for metric in spec.metrics}
        for run in runs:
            unknown_metrics = sorted(set(run.metrics) - set(definitions))
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
            if definition.required and name not in baseline.metrics
        ]
        if missing_baseline:
            raise ValueError(
                "baseline is missing required metrics: " + ", ".join(sorted(missing_baseline))
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
                    -(item.primary_metric_value if item.primary_metric_value is not None else float("-inf")),
                    item.cost_usd,
                    item.elapsed_ms,
                    item.candidate_id,
                )
            )
        else:
            eligible_candidates.sort(
                key=lambda item: (
                    item.primary_metric_value if item.primary_metric_value is not None else float("inf"),
                    item.cost_usd,
                    item.elapsed_ms,
                    item.candidate_id,
                )
            )
        spec_digest = _canonical_digest(spec.model_dump(mode="json"))
        report_body = {
            "experiment_id": spec.experiment_id,
            "task_family": spec.task_family,
            "baseline_candidate_id": spec.baseline_candidate_id,
            "primary_metric": spec.primary_metric,
            "spec_digest": spec_digest,
            "assessments": [item.model_dump(mode="json") for item in assessments],
            "ranked_candidate_ids": [item.candidate_id for item in eligible_candidates],
        }
        report_digest = _canonical_digest(report_body)
        return ExperimentReport(**report_body, report_digest=report_digest)


__all__ = ["ExperimentEvaluator"]
