"""FastAPI router for the Knowledge Engine API.

Provides endpoints for source ingestion, text extraction, translation,
claim extraction, evidence linking, scoring, querying, provenance,
and contradiction detection.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from thalos_prime.knowledge_engine.claims.extractor import ClaimExtractor
from thalos_prime.knowledge_engine.claims.linker import EvidenceLinker
from thalos_prime.knowledge_engine.coordinates.generator import CoordinateGenerator
from thalos_prime.knowledge_engine.ingestion.source_ingester import IngestionManager
from thalos_prime.knowledge_engine.ingestion.text_extractor import TextExtractor
from thalos_prime.knowledge_engine.ingestion.translator import TranslationService
from thalos_prime.knowledge_engine.models import (
    ArtifactRecord,
    ClaimRecord,
    ClaimsResponse,
    ContradictionRecord,
    ContradictionsResponse,
    EvidenceLinkResponse,
    EvidenceSpan,
    ExtractTextResponse,
    IngestSourceRequest,
    IngestSourceResponse,
    ProvenanceResponse,
    QueryRequest,
    QueryResponse,
    ScoreResponse,
    SourceRecord,
    SourceType,
    TranslateResponse,
)
from thalos_prime.knowledge_engine.scoring.scorer import VerificationScorer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge-engine"])

_ingestion_manager = IngestionManager()
_text_extractor = TextExtractor()
_translation_service = TranslationService()
_claim_extractor = ClaimExtractor()
_evidence_linker = EvidenceLinker()
_scorer = VerificationScorer()
_coordinate_generator = CoordinateGenerator()

_ingestion_manager.initialize()
_text_extractor.initialize()
_translation_service.initialize()
_claim_extractor.initialize()
_evidence_linker.initialize()
_scorer.initialize()
_coordinate_generator.initialize()

_sources: dict[str, SourceRecord] = {}
_artifacts: dict[str, ArtifactRecord] = {}
_claims: dict[str, ClaimRecord] = {}
_evidence: dict[str, list[EvidenceSpan]] = {}


@router.post("/ingest", response_model=IngestSourceResponse)
async def ingest_source(request: IngestSourceRequest) -> IngestSourceResponse:
    """Ingest a source from URL or text.

    Args:
        request: The ingest request containing url or text.

    Returns:
        IngestSourceResponse with source_id and content_hash.

    """
    if request.source_type == SourceType.URL and request.url:
        try:
            record = _ingestion_manager.ingest_url(request.url)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    elif request.text:
        try:
            record = _ingestion_manager.ingest_text(request.text, request.metadata)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
        raise HTTPException(status_code=422, detail="Either url or text must be provided")
    _sources[record.id] = record
    return IngestSourceResponse(
        source_id=record.id,
        content_hash=record.content_hash,
        message="Source ingested successfully",
    )


@router.post("/extract/{source_id}", response_model=ExtractTextResponse)
async def extract_text(source_id: str) -> ExtractTextResponse:
    """Extract text from an ingested source.

    Args:
        source_id: The ID of the source to extract text from.

    Returns:
        ExtractTextResponse with artifact_id and extracted_text.

    """
    if source_id not in _sources:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    source = _sources[source_id]
    artifact = _text_extractor.extract(source)
    _artifacts[artifact.id] = artifact
    return ExtractTextResponse(
        artifact_id=artifact.id,
        extracted_text=artifact.extracted_text,
        method=artifact.extraction_method,
    )


@router.post("/translate/{artifact_id}", response_model=TranslateResponse)
async def translate_artifact(artifact_id: str) -> TranslateResponse:
    """Assess translation stability of an artifact.

    Args:
        artifact_id: The ID of the artifact to assess.

    Returns:
        TranslateResponse with stability_score.

    """
    if artifact_id not in _artifacts:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")
    artifact = _artifacts[artifact_id]
    _, stability = _translation_service.translate(artifact)
    return TranslateResponse(
        artifact_id=artifact_id,
        stability_score=stability,
        translated=stability >= 1.0,
    )


@router.post("/claims/{artifact_id}", response_model=ClaimsResponse)
async def extract_claims(artifact_id: str) -> ClaimsResponse:
    """Extract claims from an artifact.

    Args:
        artifact_id: The ID of the artifact to extract claims from.

    Returns:
        ClaimsResponse with list of claims.

    """
    if artifact_id not in _artifacts:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")
    artifact = _artifacts[artifact_id]
    claims = _claim_extractor.extract_claims(artifact)
    for claim in claims:
        _claims[claim.id] = claim
    return ClaimsResponse(claims=claims, count=len(claims))


@router.post("/evidence/{claim_id}/{source_id}", response_model=EvidenceLinkResponse)
async def link_evidence(claim_id: str, source_id: str) -> EvidenceLinkResponse:
    """Link evidence spans for a claim within a source.

    Args:
        claim_id: The ID of the claim.
        source_id: The ID of the source to search.

    Returns:
        EvidenceLinkResponse with evidence spans.

    """
    if claim_id not in _claims:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    if source_id not in _sources:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    claim = _claims[claim_id]
    source = _sources[source_id]
    spans = _evidence_linker.link(claim, source)
    _evidence[claim_id] = spans
    return EvidenceLinkResponse(evidence_spans=spans, count=len(spans))


@router.post("/score/{claim_id}/{source_id}", response_model=ScoreResponse)
async def score_claim(claim_id: str, source_id: str) -> ScoreResponse:
    """Score a claim against a source.

    Args:
        claim_id: The ID of the claim to score.
        source_id: The ID of the source for trust scoring.

    Returns:
        ScoreResponse with overall score and status.

    """
    if claim_id not in _claims:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    if source_id not in _sources:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    claim = _claims[claim_id]
    source = _sources[source_id]
    spans = _evidence.get(claim_id, [])
    overall_score = _scorer.score_claim(
        claim=claim,
        evidence_spans=spans,
        contradictions=[],
        source_record=source,
        translation_stability=1.0,
    )
    status = _scorer.determine_status(overall_score)
    updated_claim = ClaimRecord(
        id=claim.id,
        artifact_id=claim.artifact_id,
        text=claim.text,
        score=overall_score,
        status=status,
        created_at=claim.created_at,
    )
    _claims[claim_id] = updated_claim
    return ScoreResponse(
        claim_id=claim_id,
        overall_score=overall_score,
        status=status,
    )


@router.post("/query", response_model=QueryResponse)
async def query_knowledge(request: QueryRequest) -> QueryResponse:
    """Query the knowledge base for relevant claims.

    Args:
        request: The query request with query string and filters.

    Returns:
        QueryResponse with matching claims.

    """
    query_lower = request.query.lower()
    results = [
        claim
        for claim in _claims.values()
        if query_lower in claim.text.lower() and claim.score >= request.min_score
    ]
    results = results[: request.max_results]
    return QueryResponse(results=results, count=len(results))


@router.get("/provenance/{claim_id}", response_model=ProvenanceResponse)
async def get_provenance(claim_id: str) -> ProvenanceResponse:
    """Get provenance information for a claim.

    Args:
        claim_id: The ID of the claim.

    Returns:
        ProvenanceResponse with source, artifact, and evidence spans.

    """
    if claim_id not in _claims:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    claim = _claims[claim_id]
    artifact = _artifacts.get(claim.artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact {claim.artifact_id} not found")
    spans = _evidence.get(claim_id, [])
    return ProvenanceResponse(
        claim_id=claim_id,
        source_id=artifact.source_id,
        artifact_id=artifact.id,
        evidence_spans=spans,
    )


@router.get("/contradictions/{claim_id}", response_model=ContradictionsResponse)
async def get_contradictions(claim_id: str) -> ContradictionsResponse:
    """Get contradictions for a claim.

    Args:
        claim_id: The ID of the claim.

    Returns:
        ContradictionsResponse with any contradictions found.

    """
    if claim_id not in _claims:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    contradictions: list[ContradictionRecord] = []
    return ContradictionsResponse(
        claim_id=claim_id,
        contradictions=contradictions,
        count=0,
    )
