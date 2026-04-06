"""Sense API routes - deterministic evidence-backed query answers."""

from __future__ import annotations

import contextlib
import hashlib
import os
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from thalos_prime.api.routes.artifacts import (
    _audit_trail,
    _belief_ledger,
    _indexer,
    _presenter,
    _validation_pipeline,
)
from thalos_prime.artifacts.schema import Artifact, ValidationStatus
from thalos_prime.audit.trail import AuditEventType, AuditTrail
from thalos_prime.belief.ledger import BeliefRecord, BeliefState
from thalos_prime.library_of_sense.api.query_handler import QueryHandler
from thalos_prime.library_of_sense.core.interfaces import QueryContext, QueryDomain, RetrievalResult
from thalos_prime.library_of_sense.reasoning.symbolic_engine import SymbolicReasoningEngine
from thalos_prime.library_of_sense.retrieval.code_search import CodeSearchRetriever
from thalos_prime.library_of_sense.retrieval.computational import ComputationalRetriever
from thalos_prime.library_of_sense.retrieval.knowledge_graph import (
    GraphTriple,
    KnowledgeGraphRetriever,
)
from thalos_prime.library_of_sense.synthesis.knowledge_fusion import KnowledgeFusion

router = APIRouter()

_SENSE_AUDIT_TRAIL = AuditTrail(trail_id="sense")
_SUPPORTED_PROOF_DOMAINS = {QueryDomain.MATHEMATICS, QueryDomain.COMPUTATIONAL}
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CODE_INDEX_GLOB = "**/*.py"
_MAX_CODE_FILES = 64


class SenseQueryRequest(BaseModel):
    """Request schema for evidence-backed Sense queries."""

    query: str = Field(..., min_length=1)
    domain: QueryDomain = Field(default=QueryDomain.GENERAL)
    require_proof: bool = Field(default=False)
    include_deep_trace: bool = Field(default=False)
    seed: int = Field(default=0, ge=0)
    max_depth: int = Field(default=3, ge=1, le=8)
    timeout_seconds: float = Field(default=30.0, gt=0.0, le=120.0)


def _compute_config_hash() -> str:
    env_keys = sorted(
        key for key in os.environ if key.startswith("THALOS_") or key in {"PYTHONPATH", "LIBRARY_PATH"}
    )
    payload = "|".join(f"{key}={os.environ.get(key, '')}" for key in env_keys)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _all_records() -> list[BeliefRecord]:
    return (
        _belief_ledger.get_by_state(BeliefState.ACCEPTED)
        + _belief_ledger.get_by_state(BeliefState.PENDING)
        + _belief_ledger.get_by_state(BeliefState.DISPUTED)
        + _belief_ledger.get_by_state(BeliefState.REJECTED)
    )


def _lookup_record(artifact_id: str) -> BeliefRecord | None:
    matches = [record for record in _all_records() if record.artifact_id == artifact_id]
    return matches[0] if matches else None


def _register_code_source(handler: QueryHandler) -> None:
    retriever = CodeSearchRetriever()
    files = sorted(_REPO_ROOT.glob(_CODE_INDEX_GLOB))
    for file_path in files[:_MAX_CODE_FILES]:
        if file_path.is_file():
            with contextlib.suppress(OSError, UnicodeDecodeError):
                retriever.index_source(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    handler.register_source(retriever)


def _register_kg_source(handler: QueryHandler) -> None:
    kg = KnowledgeGraphRetriever()
    kg.initialize()
    kg.add_triple(GraphTriple(subject="ThalosPrimeLibrary", predicate="is", obj="deterministic evidence engine"))
    kg.add_triple(GraphTriple(subject="deterministic evidence engine", predicate="requires", obj="auditability"))
    kg.add_triple(GraphTriple(subject="auditability", predicate="enables", obj="high-stakes trust"))
    handler.register_source(kg)


def _register_sources_for_domain(handler: QueryHandler, domain: QueryDomain) -> None:
    if domain in {QueryDomain.GENERAL, QueryDomain.MATHEMATICS, QueryDomain.COMPUTATIONAL}:
        handler.register_source(ComputationalRetriever())
    if domain in {QueryDomain.GENERAL, QueryDomain.CODE}:
        _register_code_source(handler)
    if domain in {QueryDomain.GENERAL, QueryDomain.KNOWLEDGE_GRAPH}:
        _register_kg_source(handler)
    handler.register_synthesizer(KnowledgeFusion())
    if domain in _SUPPORTED_PROOF_DOMAINS:
        handler.register_reasoning_engine(domain, SymbolicReasoningEngine())


def _serialize_retrieval_sources(sources: list[RetrievalResult]) -> list[dict[str, object]]:
    return [source.to_dict() for source in sources]


@router.post("/query")
async def sense_query(request: SenseQueryRequest) -> dict[str, Any]:
    """Execute a deterministic evidence-backed Sense query."""
    if request.require_proof and request.domain not in _SUPPORTED_PROOF_DOMAINS:
        msg = (
            f"Proof mode requires one of {[d.value for d in sorted(_SUPPORTED_PROOF_DOMAINS)]}; "
            f"received domain={request.domain.value!r}"
        )
        raise HTTPException(status_code=422, detail=msg)

    handler = QueryHandler(seed=request.seed)
    handler.initialize()
    handler.validate()
    handler.operate()
    _register_sources_for_domain(handler, request.domain)

    ts = time.time_ns()
    context = QueryContext(
        domain=request.domain,
        require_proof=request.require_proof,
        max_depth=request.max_depth,
        timeout_seconds=request.timeout_seconds,
        seed=request.seed,
    )
    answer, synthesis = handler.handle_query_with_trace(request.query, context)

    artifact = Artifact.create(
        content=answer.answer,
        source_uris=[f"sense://{request.domain.value}"],
        metadata={
            "query_hash": hashlib.sha256(request.query.encode("utf-8")).hexdigest()[:16],
            "domain": request.domain.value,
            "proof_required": str(request.require_proof).lower(),
        },
        timestamp_ns=ts,
    )
    coordinate = _indexer.index(artifact.content).to_hex_str()
    verdict = _validation_pipeline.validate(artifact, ts)

    with contextlib.suppress(ValueError):
        _belief_ledger.admit(
            artifact=artifact,
            coordinate_hex=coordinate,
            confidence=verdict.confidence,
            timestamp_ns=ts,
        )

    if verdict.final_status is ValidationStatus.ACCEPTED:
        with contextlib.suppress(KeyError, ValueError):
            _belief_ledger.accept(artifact.artifact_id, ts)
            _audit_trail.append(
                event_type=AuditEventType.ARTIFACT_ACCEPTED,
                artifact_id=artifact.artifact_id,
                timestamp_ns=ts,
                payload={"reason": "sense_query_validation_accepted"},
            )
    elif verdict.final_status is ValidationStatus.DISPUTED:
        with contextlib.suppress(KeyError):
            _belief_ledger.dispute(artifact.artifact_id, "sense_query_disputed", ts)
            _audit_trail.append(
                event_type=AuditEventType.ARTIFACT_DISPUTED,
                artifact_id=artifact.artifact_id,
                timestamp_ns=ts,
                payload={"reason": "sense_query_disputed"},
            )
    elif verdict.final_status is ValidationStatus.REJECTED:
        with contextlib.suppress(KeyError):
            _belief_ledger.reject(artifact.artifact_id, "sense_query_rejected", ts)
            _audit_trail.append(
                event_type=AuditEventType.ARTIFACT_REJECTED,
                artifact_id=artifact.artifact_id,
                timestamp_ns=ts,
                payload={"reason": "sense_query_rejected"},
            )

    _audit_trail.append(
        event_type=AuditEventType.ARTIFACT_ADMITTED,
        artifact_id=artifact.artifact_id,
        timestamp_ns=ts,
        payload={
            "verdict": verdict.final_status.value,
            "confidence": str(verdict.confidence),
            "coordinate": coordinate,
        },
        seed=str(request.seed),
        config_hash=_compute_config_hash(),
    )
    _SENSE_AUDIT_TRAIL.append(
        event_type=AuditEventType.LIFECYCLE_MILESTONE,
        artifact_id=artifact.artifact_id,
        timestamp_ns=ts,
        payload={
            "query": request.query,
            "domain": request.domain.value,
            "proof_required": str(request.require_proof).lower(),
        },
        seed=str(request.seed),
        config_hash=_compute_config_hash(),
    )

    record = _lookup_record(artifact.artifact_id)
    if record is None:
        msg = f"Sense artifact was not persisted in belief ledger: {artifact.artifact_id}"
        raise HTTPException(status_code=500, detail=msg)

    trace = _presenter.build_proof_trace(artifact, verdict, _audit_trail, _belief_ledger)
    lineage_graph = _presenter.build_lineage_graph(artifact.artifact_id, _belief_ledger).model_dump()
    artifact_events = _audit_trail.get_events_for_artifact(artifact.artifact_id)

    response: dict[str, Any] = {
        "schema_version": "1.0",
        "query": answer.query,
        "answer": answer.answer,
        "confidence": answer.confidence,
        "verified": answer.verified,
        "domain": answer.domain,
        "sources": answer.sources,
        "reasoning_steps": answer.reasoning_steps,
        "generated_at": answer.generated_at.isoformat(),
        "response_at": time.time(),
        "provenance": {
            "retrieval_sources": _serialize_retrieval_sources(synthesis.sources),
            "artifact_epistemics": {
                "artifact_id": artifact.artifact_id,
                "coordinate_hex": coordinate,
                "validation_status": verdict.final_status.value,
                "validation_confidence": verdict.confidence,
                "belief_state": record.state.value,
                "lineage": record.lineage,
            },
            "audit_chain": {
                "artifact_event_ids": [event.event_id for event in artifact_events],
                "artifact_event_count": len(artifact_events),
                "artifact_head_hash": artifact_events[-1].entry_hash if artifact_events else "",
                "sense_trail_head_hash": _SENSE_AUDIT_TRAIL.head_hash,
            },
            "proof_trace": trace.model_dump(),
            "deterministic": {
                "seed": request.seed,
                "config_hash": _compute_config_hash(),
            },
            "why_this_answer": {
                "confidence": answer.confidence,
                "verified": answer.verified,
                "reasoning_steps": answer.reasoning_steps,
            },
        },
    }
    if request.include_deep_trace:
        response["provenance"]["lineage_graph"] = lineage_graph

    handler.reconcile()
    handler.checkpoint()
    handler.terminate()
    return response

