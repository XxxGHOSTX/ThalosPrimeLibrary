"""Evidence-oriented experiment and candidate-comparison tools."""

from thalos_prime.experiments.artifact_adapter import (
    project_inventory_to_artifact,
    report_to_artifact,
)
from thalos_prime.experiments.contracts import (
    CandidateAssessment,
    CandidateRun,
    MAX_EXPERIMENT_RUNS,
    MAX_METRICS_PER_RUN,
    MAX_SAMPLES_PER_METRIC,
    MAX_EVIDENCE_REFERENCES,
    ExperimentReport,
    ExperimentSpec,
    MetricComparison,
    MetricDefinition,
    MetricDirection,
)
from thalos_prime.experiments.directive import (
    HumanDirectiveRecord,
    authorize_experiment_operation,
)
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
    "authorize_experiment_operation",
    "DuplicateFileGroup",
    "ExperimentEvaluator",
    "ExperimentPlan",
    "ExperimentReport",
    "ExperimentSpec",
    "HumanDirectiveRecord",
    "ImportEdge",
    "InventoryFile",
    "MetricComparison",
    "MetricDefinition",
    "MetricDirection",
    "MAX_EXPERIMENT_RUNS",
    "MAX_METRICS_PER_RUN",
    "MAX_SAMPLES_PER_METRIC",
    "MAX_EVIDENCE_REFERENCES",
    "ProjectInventory",
    "ProjectInventoryBuilder",
    "PythonParseIssue",
    "StageSpec",
    "default_research_plan",
    "project_inventory_to_artifact",
    "report_to_artifact",
]
