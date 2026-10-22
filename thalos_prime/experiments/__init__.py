"""Evidence-oriented experiment and candidate-comparison tools."""

from thalos_prime.experiments.contracts import (
    CandidateAssessment,
    CandidateRun,
    ExperimentReport,
    ExperimentSpec,
    MetricComparison,
    MetricDefinition,
    MetricDirection,
)
from thalos_prime.experiments.evaluator import ExperimentEvaluator
from thalos_prime.experiments.artifact_adapter import report_to_artifact

__all__ = [
    "CandidateAssessment",
    "CandidateRun",
    "ExperimentEvaluator",
    "ExperimentReport",
    "ExperimentSpec",
    "MetricComparison",
    "MetricDefinition",
    "MetricDirection",
    "report_to_artifact",
]
