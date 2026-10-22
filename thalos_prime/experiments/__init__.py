"""Evidence-oriented experiment and candidate-comparison tools."""

from thalos_prime.experiments.artifact_adapter import (
    project_inventory_to_artifact,
    report_to_artifact,
    workflow_report_to_artifact,
)
from thalos_prime.experiments.contracts import (
    CandidateAssessment,
    CandidateRun,
    ExperimentReport,
    ExperimentSpec,
    MAX_EVIDENCE_REFERENCES,
    MAX_EXPERIMENT_RUNS,
    MAX_METRICS_PER_RUN,
    MAX_SAMPLES_PER_METRIC,
    MetricComparison,
    MetricDefinition,
    MetricDirection,
)
from thalos_prime.experiments.directive import (
    HumanDirectiveRecord,
    authorize_experiment_operation,
)
from thalos_prime.experiments.evaluator import ExperimentEvaluator
from thalos_prime.experiments.execution import (
    StageContext,
    StageHandler,
    StageStatus,
    WorkflowExecutionReport,
    WorkflowExecutor,
    WorkflowStageResult,
)
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
    "authorize_experiment_operation",
    "CandidateAssessment",
    "CandidateRun",
    "default_research_plan",
    "DuplicateFileGroup",
    "ExperimentEvaluator",
    "ExperimentPlan",
    "ExperimentReport",
    "ExperimentSpec",
    "HumanDirectiveRecord",
    "ImportEdge",
    "InventoryFile",
    "MAX_EVIDENCE_REFERENCES",
    "MAX_EXPERIMENT_RUNS",
    "MAX_METRICS_PER_RUN",
    "MAX_SAMPLES_PER_METRIC",
    "MetricComparison",
    "MetricDefinition",
    "MetricDirection",
    "project_inventory_to_artifact",
    "ProjectInventory",
    "ProjectInventoryBuilder",
    "PythonParseIssue",
    "report_to_artifact",
    "StageContext",
    "StageHandler",
    "StageSpec",
    "StageStatus",
    "workflow_report_to_artifact",
    "WorkflowExecutionReport",
    "WorkflowExecutor",
    "WorkflowStageResult",
]
