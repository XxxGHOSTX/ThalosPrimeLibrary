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

__all__ = [
    "CandidateAssessment",
    "CandidateRun",
    "ExperimentEvaluator",
    "ExperimentReport",
    "ExperimentSpec",
    "MetricComparison",
    "MetricDefinition",
    "MetricDirection",
]
