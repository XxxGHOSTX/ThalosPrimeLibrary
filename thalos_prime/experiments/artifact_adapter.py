"""Adapter for storing experiment reports in ThalosPrime's artifact system."""

from __future__ import annotations

import json

from thalos_prime.artifacts.schema import Artifact
from thalos_prime.experiments.contracts import ExperimentReport


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
    evidence_refs = sorted(
        {
            evidence_ref
            for assessment in report.assessments
            for evidence_ref in assessment.evidence_refs
        }
    )
    return Artifact.create(
        content=content,
        source_uris=evidence_refs,
        metadata={
            "artifact_kind": "experiment_report",
            "experiment_id": report.experiment_id,
            "baseline_candidate_id": report.baseline_candidate_id,
            "primary_metric": report.primary_metric,
            "report_digest": report.report_digest,
        },
        timestamp_ns=timestamp_ns,
    )


__all__ = ["report_to_artifact"]
