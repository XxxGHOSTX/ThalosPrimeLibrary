"""Typed contracts for evidence-oriented candidate evaluation.

This module deliberately contains data structures only. It does not execute
model output, shell commands, arbitrary Python, or generated implementations.
"""

from __future__ import annotations

from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MetricDirection(StrEnum):
    """Direction that makes a metric better."""

    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class MetricDefinition(BaseModel):
    """A metric and its optional predeclared acceptance threshold."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    direction: MetricDirection
    required: bool = True
    target_value: float | None = Field(default=None, allow_inf_nan=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Reject names that are empty after trimming."""
        value = value.strip()
        if not value:
            raise ValueError("metric name must not be blank")
        return value


class ExperimentSpec(BaseModel):
    """Predeclared task, baseline, metrics, and evidence requirements."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: str = Field(min_length=1)
    task_family: str = Field(min_length=1)
    task_description: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    baseline_candidate_id: str = Field(min_length=1)
    primary_metric: str = Field(min_length=1)
    metrics: list[MetricDefinition] = Field(min_length=1)
    require_evidence: bool = True
    configuration_digest: str | None = None

    @model_validator(mode="after")
    def validate_metric_definitions(self) -> ExperimentSpec:
        """Require unique metrics and a required primary metric."""
        names = [metric.name for metric in self.metrics]
        if len(names) != len(set(names)):
            raise ValueError("metric names must be unique")
        by_name = {metric.name: metric for metric in self.metrics}
        if self.primary_metric not in by_name:
            raise ValueError("primary_metric must name a declared metric")
        if not by_name[self.primary_metric].required:
            raise ValueError("primary_metric must be required")
        if not self.baseline_candidate_id.strip():
            raise ValueError("baseline_candidate_id must not be blank")
        return self


class CandidateRun(BaseModel):
    """Recorded output from evaluating one solution or representation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1)
    approach: str = Field(min_length=1)
    representation_id: str = Field(min_length=1)
    implementation_version: str = Field(min_length=1)
    metrics: dict[str, float]
    tests_passed: bool
    test_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    elapsed_ms: float = Field(ge=0, allow_inf_nan=False)
    cost_usd: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    failure_summary: list[str] = Field(default_factory=list)

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, values: dict[str, float]) -> dict[str, float]:
        """Reject blank metric names and non-finite measurements."""
        for name, value in values.items():
            if not name.strip():
                raise ValueError("metric names must not be blank")
            if not isfinite(value):
                raise ValueError(f"metric {name!r} must be finite")
        return values

    @field_validator("candidate_id", "approach", "representation_id", "implementation_version")
    @classmethod
    def validate_nonblank_strings(cls, value: str) -> str:
        """Reject identifiers and labels that only contain whitespace."""
        value = value.strip()
        if not value:
            raise ValueError("candidate identifiers and labels must not be blank")
        return value


class MetricComparison(BaseModel):
    """Comparison against the baseline; positive improvement is always better."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_value: float
    candidate_value: float
    absolute_delta: float
    directed_improvement: float
    relative_improvement_percent: float | None
    improved: bool
    meets_target: bool | None


class CandidateAssessment(BaseModel):
    """Eligibility and measured results for one candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    approach: str
    representation_id: str
    implementation_version: str
    eligible: bool
    exclusion_reasons: list[str]
    primary_metric_value: float | None
    primary_improvement: float | None
    relative_primary_improvement_percent: float | None
    metric_comparisons: dict[str, MetricComparison]
    tests_passed: bool
    evidence_refs: list[str]
    elapsed_ms: float
    cost_usd: float
    failure_summary: list[str]


class ExperimentReport(BaseModel):
    """Reproducible comparison report with a digest of the report contents."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: str
    task_family: str
    baseline_candidate_id: str
    primary_metric: str
    spec_digest: str
    assessments: list[CandidateAssessment]
    ranked_candidate_ids: list[str]
    report_digest: str


__all__ = [
    "CandidateAssessment",
    "CandidateRun",
    "ExperimentReport",
    "ExperimentSpec",
    "MetricComparison",
    "MetricDefinition",
    "MetricDirection",
]
