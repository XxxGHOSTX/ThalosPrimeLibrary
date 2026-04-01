"""Presentation and export layer for ThalosPrime Library.

Data Plane module: provides JSON export, proof trace bundles, and lineage
graphs. No lifecycle orchestration — pure data transformation.

This module deliberately has NO lifecycle methods because it is a Data Plane
component; it performs no coordination or state management.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from thalos_prime.artifacts.schema import Artifact
    from thalos_prime.audit.trail import AuditTrail
    from thalos_prime.belief.ledger import BeliefLedger
    from thalos_prime.validation.pipeline import ValidationVerdict

logger = logging.getLogger(__name__)


class ProofTrace(BaseModel):
    """Proof trace bundle for a single artifact.

    Attributes:
        trace_id: SHA-256 of artifact_id + timestamp_ns.
        artifact_id: The artifact this trace covers.
        derivation_steps: Ordered derivation step records.
        validation_stages: Per-stage validation outcomes.
        audit_events: Relevant audit log entries.
        lineage: Ordered ancestor artifact IDs (oldest first).
        timestamp_ns: Nanosecond-precision creation timestamp.
        schema_version: Schema version for forward compatibility.
    """

    trace_id: str
    artifact_id: str
    derivation_steps: list[dict[str, str]]
    validation_stages: list[dict[str, object]]
    audit_events: list[dict[str, str]]
    lineage: list[str]
    timestamp_ns: int
    schema_version: int = Field(default=1)


class LineageGraph(BaseModel):
    """Lineage graph for an artifact and its ancestors.

    Attributes:
        graph_id: SHA-256 of root_artifact_id + timestamp_ns.
        root_artifact_id: The artifact at the root of the graph.
        nodes: Graph nodes — each has artifact_id, state, confidence.
        edges: Directed parent→child edges.
        timestamp_ns: Nanosecond-precision creation timestamp.
    """

    graph_id: str
    root_artifact_id: str
    nodes: list[dict[str, str]]
    edges: list[dict[str, str]]
    timestamp_ns: int


class ExportPresenter:
    """Data Plane export utility.

    Transforms artifacts, verdicts, audit trails, and belief ledger state
    into structured export formats (JSON, ProofTrace, LineageGraph).

    This class has NO lifecycle methods — it is a pure Data Plane component.

    Attributes:
        presenter_id: Deterministic identifier for this presenter instance.
    """

    def __init__(self, presenter_id: str) -> None:
        """Initialise the presenter.

        Args:
            presenter_id: Deterministic identifier for this instance.
        """
        self._presenter_id = presenter_id

    @property
    def presenter_id(self) -> str:
        """Return the presenter identifier."""
        return self._presenter_id

    def export_artifact_json(self, artifact: Artifact) -> dict[str, object]:
        """Serialise an artifact to a plain dict.

        Args:
            artifact: The artifact to export.

        Returns:
            Dict representation of the artifact (model_dump()).
        """
        return artifact.model_dump()  # type: ignore[return-value]

    def build_proof_trace(
        self,
        artifact: Artifact,
        verdict: ValidationVerdict,
        audit_trail: AuditTrail,
        belief_ledger: BeliefLedger,
    ) -> ProofTrace:
        """Assemble a ProofTrace from artifact, verdict, audit, and ledger data.

        Args:
            artifact: The artifact to trace.
            verdict: Validation verdict for the artifact.
            audit_trail: Audit trail to pull events from.
            belief_ledger: Belief ledger for lineage lookup.

        Returns:
            A fully populated :class:`ProofTrace`.
        """
        trace_id_raw = (artifact.artifact_id + str(verdict.timestamp_ns)).encode(
            "utf-8"
        )
        trace_id = hashlib.sha256(trace_id_raw).hexdigest()

        derivation_steps: list[dict[str, str]] = []
        if artifact.provenance:
            for step in artifact.provenance.derivation_steps:
                derivation_steps.append(
                    {
                        "step_id": step.step_id,
                        "operation": step.operation,
                        "output_id": step.output_id,
                    }
                )

        validation_stages: list[dict[str, object]] = [
            {
                "stage": sr.stage.value,
                "passed": sr.passed,
                "score": sr.score,
                "notes": sr.notes,
            }
            for sr in verdict.stage_results
        ]

        audit_events: list[dict[str, str]] = [
            {
                "event_id": ev.event_id,
                "event_type": ev.event_type.value,
                "artifact_id": ev.artifact_id or "",
                "timestamp_ns": str(ev.timestamp_ns),
            }
            for ev in audit_trail.get_events_for_artifact(artifact.artifact_id)
        ]

        lineage_records = belief_ledger.get_lineage(artifact.artifact_id)
        lineage = [r.artifact_id for r in lineage_records]

        return ProofTrace(
            trace_id=trace_id,
            artifact_id=artifact.artifact_id,
            derivation_steps=derivation_steps,
            validation_stages=validation_stages,
            audit_events=audit_events,
            lineage=lineage,
            timestamp_ns=verdict.timestamp_ns,
        )

    def build_lineage_graph(
        self,
        artifact_id: str,
        belief_ledger: BeliefLedger,
    ) -> LineageGraph:
        """Build a lineage graph for an artifact.

        Args:
            artifact_id: Root artifact to trace.
            belief_ledger: Ledger to traverse for lineage.

        Returns:
            A :class:`LineageGraph` with nodes and directed edges.
        """
        graph_id_raw = (artifact_id + "lineage").encode("utf-8")
        graph_id = hashlib.sha256(graph_id_raw).hexdigest()

        lineage_records = belief_ledger.get_lineage(artifact_id)

        nodes: list[dict[str, str]] = [
            {
                "artifact_id": r.artifact_id,
                "state": r.state.value,
                "confidence": str(r.confidence),
            }
            for r in lineage_records
        ]

        edges: list[dict[str, str]] = []
        for i in range(len(lineage_records) - 1):
            edges.append(
                {
                    "from": lineage_records[i].artifact_id,
                    "to": lineage_records[i + 1].artifact_id,
                    "relation": "parent",
                }
            )

        return LineageGraph(
            graph_id=graph_id,
            root_artifact_id=artifact_id,
            nodes=nodes,
            edges=edges,
            timestamp_ns=0,
        )

    def export_to_json(
        self,
        data: dict[str, object] | ProofTrace | LineageGraph,
    ) -> str:
        """Serialise data to a deterministic JSON string.

        Args:
            data: A dict, ProofTrace, or LineageGraph to serialise.

        Returns:
            JSON string with sorted keys and 2-space indentation.
        """
        if isinstance(data, (ProofTrace, LineageGraph)):
            raw: Any = data.model_dump()
        else:
            raw = data
        return json.dumps(raw, sort_keys=True, indent=2, default=str)
