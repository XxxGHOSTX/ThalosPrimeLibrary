"""Adapter for storing experiment reports in ThalosPrime's artifact system."""

from __future__ import annotations

import json

from thalos_prime.artifacts.schema import Artifact
from thalos_prime.experiments.contracts import ExperimentReport
from thalos_prime.experiments.project_inventory import ProjectInventory


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

    This creates a record for downstream validation and provenance; it does
    not admit the inventory to the belief ledger or assert that its static
    import graph captures all runtime dependencies.
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


__all__ = ["project_inventory_to_artifact", "report_to_artifact"]
