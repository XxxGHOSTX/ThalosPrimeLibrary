"""Artifact API routes for ThalosPrime Library.

Provides REST endpoints for artifact ingestion, derivation, retrieval,
export, and consensus operations backed by the Canonical Artifact Schema,
Belief Base, Validation Pipeline, and Audit Trail subsystems.
"""

from __future__ import annotations

import contextlib
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from thalos_prime.artifacts.schema import Artifact, GenesisLock, ValidationStatus
from thalos_prime.audit.trail import AuditEventType, AuditTrail
from thalos_prime.belief.ledger import BeliefLedger, BeliefState
from thalos_prime.export.presenter import ExportPresenter
from thalos_prime.indexing.prp import PrpIndexer
from thalos_prime.reasoning_tpl.derive import DeriveOperation, TplReasoningLayer
from thalos_prime.validation.pipeline import ValidationPipeline

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Module-level singletons — initialised once at import time.
# All keys are fixed for deterministic behaviour; swap via env-vars in prod.
# ---------------------------------------------------------------------------
_HMAC_KEY: bytes = b"thalos-prime-genesis-lock!!!!!!!!"  # nosec S105
_PRP_KEY: bytes = b"thalos-prime-prp!!"  # nosec S105

_genesis_lock = GenesisLock(key=_HMAC_KEY[:32])
_indexer = PrpIndexer(key=_PRP_KEY)
_belief_ledger = BeliefLedger(ledger_id="primary")
_audit_trail = AuditTrail(trail_id="primary")
_validation_pipeline = ValidationPipeline(
    pipeline_id="primary", belief_ledger=_belief_ledger
)
_reasoning_layer = TplReasoningLayer(
    layer_id="primary",
    belief_ledger=_belief_ledger,
    validation_pipeline=_validation_pipeline,
    audit_trail=_audit_trail,
)
_presenter = ExportPresenter(presenter_id="primary")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class IngestRequest(BaseModel):
    """Request body for POST /ingest."""

    content: str
    source_uris: list[str]
    metadata: dict[str, str] | None = None


class DeriveRequest(BaseModel):
    """Request body for POST /derive."""

    artifact_ids: list[str]
    operation: str = "synthesize"


class ConsensusRequest(BaseModel):
    """Request body for POST /consensus."""

    artifact_ids: list[str]
    min_confidence: float = 0.5


class ConsensusResponse(BaseModel):
    """Response for POST /consensus."""

    consensus_artifact_id: str | None
    agreement_score: float
    participant_count: int
    message: str


class ContradictionRequest(BaseModel):
    """Request body for POST /contradictions."""

    artifact_ids: list[str]


class EvidenceWorkflowItem(BaseModel):
    """Single ingestion item for deterministic evidence workflow."""

    content: str
    source_uris: list[str]
    metadata: dict[str, str] | None = None


class EvidenceWorkflowRequest(BaseModel):
    """Request body for POST /workflow/evidence_bundle."""

    items: list[EvidenceWorkflowItem]
    derive_operation: str = "synthesize"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/ingest")
async def ingest_artifact(request: IngestRequest) -> dict[str, Any]:
    """Ingest an artifact, run the 6-stage validation pipeline, and admit.

    The artifact is canonicalised, assigned an identity coordinate via the
    PRP indexer, and admitted to the Belief Base as PENDING.  If the
    validation verdict is ACCEPTED the record is immediately transitioned.

    Returns:
        Dict with artifact JSON and validation verdict.

    """
    ts = time.time_ns()
    artifact = Artifact.create(
        content=request.content,
        source_uris=request.source_uris,
        metadata=request.metadata or {},
        timestamp_ns=ts,
    )
    coord = _indexer.index(artifact.content)

    verdict = _validation_pipeline.validate(artifact, ts)

    with contextlib.suppress(ValueError):
        _belief_ledger.admit(
            artifact=artifact,
            coordinate_hex=coord.to_hex_str(),
            confidence=verdict.confidence,
            timestamp_ns=ts,
        )

    if verdict.final_status is ValidationStatus.ACCEPTED:
        with contextlib.suppress(KeyError, ValueError):
            _belief_ledger.accept(artifact.artifact_id, ts)

    _audit_trail.append(
        event_type=AuditEventType.ARTIFACT_ADMITTED,
        artifact_id=artifact.artifact_id,
        timestamp_ns=ts,
        payload={
            "verdict": verdict.final_status.value,
            "confidence": str(verdict.confidence),
            "coordinate": coord.to_hex_str(),
        },
    )

    return {
        "artifact": _presenter.export_artifact_json(artifact),
        "verdict": {
            "final_status": verdict.final_status.value,
            "confidence": verdict.confidence,
            "coordinate": coord.to_hex_str(),
        },
    }


@router.get("/artifact/{artifact_id}")
async def get_artifact(artifact_id: str) -> dict[str, Any]:
    """Retrieve the Belief Record for an artifact by ID.

    Args:
        artifact_id: SHA-256 hex identity of the artifact.

    Returns:
        Dict with belief record fields.

    Raises:
        HTTPException(404): When the artifact_id is not in the ledger.

    """
    record = _belief_ledger.resolve_by_coordinate(artifact_id)
    # resolve_by_coordinate looks up by coordinate_hex; try artifact_id directly
    if record is None:
        all_records = (
            _belief_ledger.get_by_state(BeliefState.ACCEPTED)
            + _belief_ledger.get_by_state(BeliefState.PENDING)
            + _belief_ledger.get_by_state(BeliefState.DISPUTED)
            + _belief_ledger.get_by_state(BeliefState.REJECTED)
        )
        matches = [r for r in all_records if r.artifact_id == artifact_id]
        record = matches[0] if matches else None

    if record is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    return record.model_dump()


@router.post("/derive")
async def derive_artifact(request: DeriveRequest) -> dict[str, Any]:
    """Derive a new claim from ACCEPTED artifacts.

    Args (body):
        artifact_ids: List of ACCEPTED artifact IDs to derive from.
        operation: Derivation strategy (synthesize/summarize/extract/infer/combine).

    Returns:
        Dict with candidate_claim and validation verdict.

    Raises:
        HTTPException(400): When artifact_ids are not found or not ACCEPTED,
            or operation is unknown.

    """
    ts = time.time_ns()
    try:
        op = DeriveOperation(request.operation.lower())
    except ValueError:
        valid = [o.value for o in DeriveOperation]
        raise HTTPException(
            status_code=400,
            detail=f"Unknown operation {request.operation!r}. Valid: {valid}",
        )

    try:
        candidate, verdict = _reasoning_layer.derive(
            artifact_ids=request.artifact_ids,
            operation=op,
            timestamp_ns=ts,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "candidate_claim": candidate.model_dump(),
        "verdict": {
            "final_status": verdict.final_status.value,
            "confidence": verdict.confidence,
        },
    }


@router.get("/export/{artifact_id}")
async def export_artifact(artifact_id: str) -> dict[str, Any]:
    """Export an artifact as JSON with a proof trace bundle.

    Args:
        artifact_id: SHA-256 hex identity of the artifact.

    Returns:
        Dict with artifact JSON and proof trace.

    Raises:
        HTTPException(404): When the artifact_id is not in the ledger.

    """
    all_records = (
        _belief_ledger.get_by_state(BeliefState.ACCEPTED)
        + _belief_ledger.get_by_state(BeliefState.PENDING)
        + _belief_ledger.get_by_state(BeliefState.DISPUTED)
        + _belief_ledger.get_by_state(BeliefState.REJECTED)
    )
    matches = [r for r in all_records if r.artifact_id == artifact_id]
    if not matches:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    record = matches[0]
    # Re-create a minimal Artifact for export (content is not stored in BeliefRecord)
    ts = time.time_ns()
    stub = Artifact.create(
        content=record.coordinate_hex,
        source_uris=[f"belief:{artifact_id}"],
        metadata={"exported_from": "belief_ledger"},
        timestamp_ns=ts,
    )
    # Override artifact_id to match original
    object.__setattr__(stub, "artifact_id", artifact_id)

    verdict = _validation_pipeline.validate(stub, ts)
    trace = _presenter.build_proof_trace(stub, verdict, _audit_trail, _belief_ledger)

    return {
        "artifact": _presenter.export_artifact_json(stub),
        "proof_trace": trace.model_dump(),
        "belief_record": record.model_dump(),
    }


@router.get("/graph/{artifact_id}")
async def get_lineage_graph(artifact_id: str) -> dict[str, Any]:
    """Return the lineage graph for an artifact.

    Args:
        artifact_id: SHA-256 hex identity of the artifact.

    Returns:
        Serialised LineageGraph.

    Raises:
        HTTPException(404): When the artifact_id is not in the ledger.

    """
    all_records = (
        _belief_ledger.get_by_state(BeliefState.ACCEPTED)
        + _belief_ledger.get_by_state(BeliefState.PENDING)
        + _belief_ledger.get_by_state(BeliefState.DISPUTED)
        + _belief_ledger.get_by_state(BeliefState.REJECTED)
    )
    matches = [r for r in all_records if r.artifact_id == artifact_id]
    if not matches:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    graph = _presenter.build_lineage_graph(artifact_id, _belief_ledger)
    return graph.model_dump()


@router.post("/consensus")
async def consensus(request: ConsensusRequest) -> ConsensusResponse:
    """Find the highest-confidence ACCEPTED artifact among a set of candidates.

    Args (body):
        artifact_ids: Candidate artifact IDs to evaluate.
        min_confidence: Minimum confidence threshold (default 0.5).

    Returns:
        ConsensusResponse identifying the winning artifact or None.

    """
    accepted = _belief_ledger.get_by_state(BeliefState.ACCEPTED)
    candidates = [
        r
        for r in accepted
        if r.artifact_id in request.artifact_ids
        and r.confidence >= request.min_confidence
    ]

    if not candidates:
        return ConsensusResponse(
            consensus_artifact_id=None,
            agreement_score=0.0,
            participant_count=len(request.artifact_ids),
            message="No accepted artifacts meet the confidence threshold.",
        )

    winner = max(candidates, key=lambda r: r.confidence)
    avg_score = sum(r.confidence for r in candidates) / len(candidates)

    return ConsensusResponse(
        consensus_artifact_id=winner.artifact_id,
        agreement_score=round(avg_score, 4),
        participant_count=len(candidates),
        message=f"Consensus reached: {winner.artifact_id[:16]}... (confidence={winner.confidence:.3f})",
    )


@router.post("/contradictions")
async def contradictions(request: ContradictionRequest) -> dict[str, Any]:
    """Return contradiction intelligence over a set of artifact IDs.

    Exposes top-level disagreement signals with explicit reason labels:
    - state disagreement (accepted/disputed/rejected mismatch)
    - confidence divergence (spread > 0.2)
    - explicit FACS contradiction links
    """
    if not request.artifact_ids:
        return {
            "artifact_ids": [],
            "contradictions": [],
            "consensus_score": 1.0,
            "message": "No artifact IDs provided; no contradictions.",
        }

    all_records = (
        _belief_ledger.get_by_state(BeliefState.ACCEPTED)
        + _belief_ledger.get_by_state(BeliefState.PENDING)
        + _belief_ledger.get_by_state(BeliefState.DISPUTED)
        + _belief_ledger.get_by_state(BeliefState.REJECTED)
    )
    index = {record.artifact_id: record for record in all_records}
    selected = [index[artifact_id] for artifact_id in request.artifact_ids if artifact_id in index]

    if not selected:
        return {
            "artifact_ids": request.artifact_ids,
            "contradictions": [],
            "consensus_score": 0.0,
            "message": "No provided artifact IDs exist in the belief ledger.",
        }

    states = {record.state.value for record in selected}
    state_contradiction = len(states) > 1
    confidences = [record.confidence for record in selected]
    confidence_spread = max(confidences) - min(confidences)
    confidence_contradiction = confidence_spread > 0.2
    facs_links = [
        {
            "artifact_id": record.artifact_id,
            "facs_flags": record.facs_flags,
            "lineage": record.lineage,
        }
        for record in selected
        if record.facs_flags.get("disputed", False) or record.facs_flags.get("rejected", False)
    ]

    contradictions_payload: list[dict[str, Any]] = []
    if state_contradiction:
        contradictions_payload.append(
            {
                "type": "state_disagreement",
                "reason": "Artifacts span multiple belief states",
                "states": sorted(states),
            }
        )
    if confidence_contradiction:
        contradictions_payload.append(
            {
                "type": "confidence_divergence",
                "reason": "Confidence spread exceeds deterministic threshold",
                "spread": round(confidence_spread, 4),
            }
        )
    if facs_links:
        contradictions_payload.append(
            {
                "type": "facs_dispute_or_reject",
                "reason": "One or more artifacts carry disputed/rejected FACS flags",
                "records": facs_links,
            }
        )

    contradictory_count = sum(1 for record in selected if record.state in {BeliefState.DISPUTED, BeliefState.REJECTED})
    consensus_score = 1.0 - (contradictory_count / len(selected))
    return {
        "artifact_ids": request.artifact_ids,
        "resolved_records": [record.model_dump() for record in selected],
        "contradictions": contradictions_payload,
        "consensus_score": round(consensus_score, 4),
        "message": (
            "Contradictions detected." if contradictions_payload else "No contradictions detected."
        ),
    }


@router.post("/workflow/evidence_bundle")
async def evidence_bundle_workflow(request: EvidenceWorkflowRequest) -> dict[str, Any]:
    """Run deterministic end-to-end evidence workflow.

    Pipeline:
    ingest corpus -> validate beliefs -> derive claim (from accepted) -> export proof bundle.
    """
    if not request.items:
        raise HTTPException(status_code=422, detail="items must contain at least one entry")

    try:
        operation = DeriveOperation(request.derive_operation.lower())
    except ValueError as exc:
        valid = [enum.value for enum in DeriveOperation]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid derive_operation {request.derive_operation!r}. Valid values: {valid}",
        ) from exc

    ts_base = time.time_ns()
    ingested: list[dict[str, Any]] = []
    accepted_ids: list[str] = []
    trace_bundle: list[dict[str, Any]] = []

    for idx, item in enumerate(request.items):
        ts = ts_base + idx
        artifact = Artifact.create(
            content=item.content,
            source_uris=item.source_uris,
            metadata=item.metadata or {},
            timestamp_ns=ts,
        )
        coord = _indexer.index(artifact.content)
        verdict = _validation_pipeline.validate(artifact, ts)

        with contextlib.suppress(ValueError):
            _belief_ledger.admit(
                artifact=artifact,
                coordinate_hex=coord.to_hex_str(),
                confidence=verdict.confidence,
                timestamp_ns=ts,
            )

        if verdict.final_status is ValidationStatus.ACCEPTED:
            with contextlib.suppress(KeyError, ValueError):
                _belief_ledger.accept(artifact.artifact_id, ts)
                accepted_ids.append(artifact.artifact_id)

        _audit_trail.append(
            event_type=AuditEventType.ARTIFACT_ADMITTED,
            artifact_id=artifact.artifact_id,
            timestamp_ns=ts,
            payload={
                "verdict": verdict.final_status.value,
                "confidence": str(verdict.confidence),
                "coordinate": coord.to_hex_str(),
            },
        )
        trace = _presenter.build_proof_trace(artifact, verdict, _audit_trail, _belief_ledger)
        ingested.append(
            {
                "artifact": _presenter.export_artifact_json(artifact),
                "verdict": {
                    "final_status": verdict.final_status.value,
                    "confidence": verdict.confidence,
                    "coordinate": coord.to_hex_str(),
                },
            }
        )
        trace_bundle.append(trace.model_dump())

    derivation_result: dict[str, Any] | None = None
    if accepted_ids:
        derive_ts = ts_base + len(request.items) + 1
        candidate, derive_verdict = _reasoning_layer.derive(
            artifact_ids=accepted_ids,
            operation=operation,
            timestamp_ns=derive_ts,
        )
        derivation_result = {
            "candidate_claim": candidate.model_dump(),
            "verdict": {
                "final_status": derive_verdict.final_status.value,
                "confidence": derive_verdict.confidence,
            },
        }

    return {
        "workflow": "evidence_bundle",
        "inputs": len(request.items),
        "accepted_artifacts": accepted_ids,
        "ingested": ingested,
        "derivation": derivation_result,
        "proof_bundle": trace_bundle,
    }
