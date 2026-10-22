"""Tests for workflow-report persistence through the canonical artifact schema."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from thalos_prime.experiments import (
    ExperimentSpec,
    HumanDirectiveRecord,
    MetricDefinition,
    MetricDirection,
    StageSpec,
    WorkflowExecutor,
    workflow_report_to_artifact,
)
from thalos_prime.experiments.plan import ExperimentPlan


def build_report():
    """Create a deterministic one-stage run for adapter tests."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    directive = HumanDirectiveRecord(
        directive_id="workflow-artifact-directive",
        timestamp=datetime(2026, 10, 22, tzinfo=timezone.utc),
        objectives=["Record a test workflow"],
        success_criteria=["Capture stage digest"],
        permitted_operations=["inspect"],
    )
    directive.sign(private_key, "artifact-test-signer")
    spec = ExperimentSpec(
        experiment_id="workflow-artifact-exp",
        task_family="adapter-test",
        task_description="Persist a workflow report",
        dataset_version="fixture-v1",
        baseline_candidate_id="baseline",
        primary_metric="pass_rate",
        metrics=[
            MetricDefinition(
                name="pass_rate",
                direction=MetricDirection.MAXIMIZE,
            )
        ],
        directive_id=directive.directive_id,
        directive_digest=directive.directive_digest,
    )
    plan = ExperimentPlan(
        plan_id="workflow-artifact-plan",
        stages=[StageSpec(stage_id="inspect", operation="inspect")],
    )
    executor = WorkflowExecutor()
    executor.register("inspect", lambda _context: {"checked": True})
    report = executor.execute(
        plan=plan,
        spec=spec,
        directive=directive,
        public_key=public_key,
        initial_context={},
    )
    return report


def test_workflow_report_becomes_pending_artifact_with_source_lineage() -> None:
    """Run digest, directive binding, and real source references are preserved."""
    report = build_report()
    source_uris = [
        "artifact:evidence-2",
        "artifact:evidence-1",
        "artifact:evidence-1",
    ]
    artifact = workflow_report_to_artifact(
        report,
        source_uris=source_uris,
        timestamp_ns=123456789,
    )
    assert artifact.validation_status.value == "pending"
    assert artifact.metadata["artifact_kind"] == "workflow_execution_report"
    assert artifact.metadata["report_digest"] == report.report_digest
    assert artifact.metadata["directive_id"] == report.directive_id
    assert artifact.metadata["directive_digest"] == report.directive_digest
    assert artifact.source_uris == ["artifact:evidence-1", "artifact:evidence-2"]
    assert artifact.timestamp_ns == 123456789


def test_workflow_report_requires_real_source_references() -> None:
    """The adapter does not invent a URI when evidence provenance is absent."""
    report = build_report()
    with pytest.raises(ValueError, match="at least one real source URI"):
        workflow_report_to_artifact(report, source_uris=[" ", ""], timestamp_ns=10)
