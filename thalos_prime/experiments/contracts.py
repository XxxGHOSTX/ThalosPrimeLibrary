"""Typed contracts for evidence-oriented candidate evaluation.

This module contains data structures only. It does not execute model output,
shell commands, arbitrary Python, or generated implementations.
"""

from __future__ import annotations

from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_HEX_LENGTH = 64
MAX_EXPERIMENT_RUNS = 25
MAX_METRICS_PER_RUN = 25
MAX_SAMPLES_PER_METRIC = 2_000
MAX_EVIDENCE_REFERENCES = 500


class MetricDirection(StrEnum):
    """Direction that makes a metric better."""

    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class MetricDefinition(BaseModel):
    """A metric and its optional predeclared acceptance threshold."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=100)
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

    experiment_id: str = Field(min_length=1, max_length=200)
    task_family: str = Field(min_length=1, max_length=200)
    task_description: str = Field(min_length=1, max_length=4_000)
    dataset_version: str = Field(min_length=1, max_length=200)
    baseline_candidate_id: str = Field(min_length=1, max_length=200)
    primary_metric: str = Field(min_length=1, max_length=100)
    metrics: list[MetricDefinition] = Field(
        min_length=1,
        max_length=MAX_METRICS_PER_RUN,
    )
    require_evidence: bool = True
    configuration_digest: str | None = None
    directive_id: str | None = None
    directive_digest: str | None = None

    @field_validator(
        "experiment_id",
        "task_family",
        "task_description",
        "dataset_version",
        "baseline_candidate_id",
        "primary_metric",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        """Normalize task identity text and reject whitespace-only values."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("experiment specification text fields must not be blank")
        return normalized

    @field_validator("directive_id")
    @classmethod
    def normalize_directive_id(cls, value: str | None) -> str | None:
        """Normalize an optional directive ID."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("directive_id must not be blank")
        return normalized

    @field_validator("configuration_digest", "directive_digest")
    @classmethod
    def validate_optional_digest(cls, value: str | None) -> str | None:
        """Require a lowercase SHA-256 hex digest when a digest is supplied."""
        if value is None:
            return None
        if (
            len(value) != _SHA256_HEX_LENGTH
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError("configuration and directive digests must be lowercase SHA-256 hex")
        return value

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
        if (self.directive_id is None) != (self.directive_digest is None):
            raise ValueError("directive_id and directive_digest must be supplied together")
        return self


class CandidateRun(BaseModel):
    """Recorded measurements for one candidate implementation or representation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    approach: str = Field(min_length=1)
    representation_id: str = Field(min_length=1)
    implementation_version: str = Field(min_length=1)
    environment_fingerprint: str = Field(min_length=1)
    model_versions: dict[str, str] = Field(default_factory=dict)
    configuration_digest: str | None = None
    metric_samples: dict[str, list[float]]
    sample_ids: list[str] = Field(default_factory=list)
    tests_passed: bool
    test_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    elapsed_ms: float = Field(ge=0, allow_inf_nan=False)
    cost_usd: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    failure_summary: list[str] = Field(default_factory=list)

    @field_validator("metric_samples")
    @classmethod
    def validate_metric_samples(cls, values: dict[str, list[float]]) -> dict[str, list[float]]:
        """Reject blank names, empty samples, and non-finite measurements."""
        for name, samples in values.items():
            if not name.strip():
                raise ValueError("metric names must not be blank")
            if not samples:
                raise ValueError(f"metric {name!r} must contain at least one sample")
            if not all(isfinite(value) for value in samples):
                raise ValueError(f"all samples for metric {name!r} must be finite")
        return values

    @field_validator(
        "run_id",
        "candidate_id",
        "approach",
        "representation_id",
        "implementation_version",
        "environment_fingerprint",
    )
    @classmethod
    def validate_nonblank_strings(cls, value: str) -> str:
        """Reject identifiers and labels that only contain whitespace."""
        value = value.strip()
        if not value:
            raise ValueError("identifiers and labels must not be blank")
        return value

    @field_validator("sample_ids")
    @classmethod
    def validate_sample_ids(cls, values: list[str]) -> list[str]:
        """Require unique, nonblank task/trial identifiers when samples are paired."""
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("sample IDs must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("sample IDs must be unique")
        return normalized

    @field_validator("configuration_digest")
    @classmethod
    def validate_configuration_digest(cls, value: str | None) -> str | None:
        """Require a lowercase SHA-256 hex digest when configuration is identified."""
        if value is None:
            return None
        if (
            len(value) != _SHA256_HEX_LENGTH
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError("configuration_digest must be a lowercase SHA-256 hex digest")
        return value

    @field_validator("model_versions")
    @classmethod
    def validate_model_versions(cls, values: dict[str, str]) -> dict[str, str]:
        """Normalize model/tool labels and reject blank or duplicate normalized names."""
        normalized: dict[str, str] = {}
        for name, version in values.items():
            normalized_name = name.strip()
            normalized_version = version.strip()
            if not normalized_name or not normalized_version:
                raise ValueError("model/tool names and versions must not be blank")
            if normalized_name in normalized:
                raise ValueError("model/tool names must remain unique after normalization")
            normalized[normalized_name] = normalized_version
        return normalized

    @model_validator(mode="after")
    def validate_sample_alignment(self) -> CandidateRun:
        """Align per-case measurements when sample IDs are supplied."""
        if self.sample_ids:
            mismatched = sorted(
                name
                for name, samples in self.metric_samples.items()
                if len(samples) != len(self.sample_ids)
            )
            if mismatched:
                raise ValueError(
                    "sample_ids length must match every metric sample list: "
                    + ", ".join(mismatched)
                )
        return self


class MetricComparison(BaseModel):
    """Comparison against a baseline; positive directed change is better."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_value: float
    candidate_value: float
    absolute_delta: float
    directed_improvement: float
    relative_improvement_percent: float | None
    improved: bool
    meets_target: bool | None
    baseline_sample_count: int = Field(ge=1)
    candidate_sample_count: int = Field(ge=1)
    baseline_sample_stddev: float | None
    candidate_sample_stddev: float | None
    paired_sample_count: int = Field(default=0, ge=0)
    paired_improvement_mean: float | None = None
    paired_improvement_stddev: float | None = None


class CandidateAssessment(BaseModel):
    """Eligibility, measured results, and provenance for one candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    candidate_id: str
    approach: str
    representation_id: str
    implementation_version: str
    environment_fingerprint: str
    model_versions: dict[str, str]
    configuration_digest: str | None
    eligible: bool
    exclusion_reasons: list[str]
    primary_metric_value: float | None
    primary_improvement: float | None
    relative_primary_improvement_percent: float | None
    metric_samples: dict[str, list[float]]
    sample_ids: list[str]
    metric_comparisons: dict[str, MetricComparison]
    tests_passed: bool
    test_ids: list[str]
    evidence_refs: list[str]
    elapsed_ms: float
    cost_usd: float
    failure_summary: list[str]


class ExperimentReport(BaseModel):
    """Reproducible report including the specification and its content digest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: str
    task_family: str
    baseline_candidate_id: str
    primary_metric: str
    spec: ExperimentSpec
    spec_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessments: list[CandidateAssessment]
    ranked_candidate_ids: list[str]
    report_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


__all__ = [
    "CandidateAssessment",
    "CandidateRun",
    "ExperimentReport",
    "ExperimentSpec",
    "MetricComparison",
    "MetricDefinition",
    "MetricDirection",
]
