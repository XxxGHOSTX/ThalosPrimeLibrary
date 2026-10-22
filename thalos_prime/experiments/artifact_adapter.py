"""Adapter for storing experiment reports in ThalosPrime's artifact system."""

from __future__ import annotations

import json

from thalos_prime.artifacts.schema import Artifact
from thalos_prime.experiments.contracts import ExperimentReport
from thalos_prime.experiments.project_inventory import ProjectInventory
from thalos_prime.experiments.execution import WorkflowExecutionReport


def report_to_artifact(report: ExperimentReport, *, timestamp_ns: int) -> Artifact:
    """Convert a report to a pending canonical artifact.

    The caller supplies the timestamp so the conversion can be reproduced.
    Evidence references are carried into the existing artifact source list.
    The returned artifact remains PENDING; this adapter does not approve a
    scientific claim or bypass the existing validation pipeline.
    """
    content = json.dumps(
        report.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    evidence_ref_set = {
        evidence_ref
        for assessment in report.assessments
        for evidence_ref in assessment.evidence_refs
    }
    if report.spec.directive_id is not None:
        evidence_ref_set.add(f"directive:{report.spec.directive_id}")
    evidence_refs = sorted(evidence_ref_set)
    metadata = {
        "artifact_kind": "experiment_report",
        "experiment_id": report.experiment_id,
        "baseline_candidate_id": report.baseline_candidate_id,
        "primary_metric": report.primary_metric,
        "report_digest": report.report_digest,
    }
    if report.spec.directive_id is not None and report.spec.directive_digest is not None:
        metadata["directive_id"] = report.spec.directive_id
        metadata["directive_digest"] = report.spec.directive_digest
    return Artifact.create(
        content=content,
        source_uris=evidence_refs,
        metadata=metadata,
        timestamp_ns=timestamp_ns,
    )


def project_inventory_to_artifact(
    inventory: ProjectInventory,
    *,
    source_uri: str,
    timestamp_ns: int,
) -> Artifact:
    """Convert a bounded project snapshot into a pending canonical artifact.

    The caller must supply a real URI identifying the inspected project. This
    adapter does not invent a provenance reference, admit the artifact to the
    belief ledger, or claim the static import graph captures runtime dependencies.
    """
    normalized_source_uri = source_uri.strip()
    if not normalized_source_uri:
        raise ValueError("source_uri must identify the inventoried project")

    content = json.dumps(
        inventory.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return Artifact.create(
        content=content,
        source_uris=[normalized_source_uri],
        metadata={
            "artifact_kind": "project_inventory",
            "root_name": inventory.root_name,
            "project_digest": inventory.project_digest,
        },
        timestamp_ns=timestamp_ns,
    )


def workflow_report_to_artifact(
    report: WorkflowExecutionReport,
    *,
    source_uris: list[str],
    timestamp_ns: int,
) -> Artifact:
    """Convert a workflow run report to a pending, source-bound artifact.

    Source references must be supplied by the caller and identify the evidence
    or task artifacts used by the run. The adapter preserves the signed
    directive and execution digests but does not auto-accept the report.
    """
    normalized_sources = sorted(
        {source_uri.strip() for source_uri in source_uris if source_uri.strip()}
    )
    if not normalized_sources:
        raise ValueError("at least one real source URI is required for workflow provenance")

    content = json.dumps(
        report.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return Artifact.create(
        content=content,
        source_uris=normalized_sources,
        metadata={
            "artifact_kind": "workflow_execution_report",
            "plan_id": report.plan_id,
            "plan_digest": report.plan_digest,
            "directive_id": report.directive_id,
            "directive_digest": report.directive_digest,
            "report_digest": report.report_digest,
            "succeeded_count": str(report.succeeded_count),
            "failed_count": str(report.failed_count),
            "blocked_count": str(report.blocked_count),
            "authorization_denied_count": str(report.authorization_denied_count),
            "approval_required_count": str(report.approval_required_count),
            "timed_out_count": str(report.timed_out_count),
        },
        timestamp_ns=timestamp_ns,
    )


__all__ = [
    "project_inventory_to_artifact",
    "report_to_artifact",
    "workflow_report_to_artifact",
]
