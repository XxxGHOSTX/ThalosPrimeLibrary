"""Evidence-oriented experiment and candidate-comparison tools."""

from thalos_prime.experiments.artifact_adapter import report_to_artifact
from thalos_prime.experiments.contracts import (
    CandidateAssessment,
    CandidateRun,
    ExperimentReport,
    ExperimentSpec,
    MetricComparison,
    MetricDefinition,
    MetricDirection,
)
from thalos_prime.experiments.directive import HumanDirectiveRecord
from thalos_prime.experiments.evaluator import ExperimentEvaluator
from thalos_prime.experiments.plan import ExperimentPlan, StageSpec, default_research_plan
from thalos_prime.experiments.project_inventory import (
    DuplicateFileGroup,
    ImportEdge,
    InventoryFile,
    ProjectInventory,
    ProjectInventoryBuilder,
    PythonParseIssue,
)

__all__ = [
    "CandidateAssessment",
    "CandidateRun",
    "ExperimentEvaluator",
    "HumanDirectiveRecord",
    "ExperimentPlan",
    "ExperimentReport",
    "ExperimentSpec",
    "DuplicateFileGroup",
    "ImportEdge",
    "InventoryFile",
    "ProjectInventory",
    "ProjectInventoryBuilder",
    "PythonParseIssue",
    "MetricComparison",
    "MetricDefinition",
    "MetricDirection",
    "StageSpec",
    "default_research_plan",
    "report_to_artifact",
]
