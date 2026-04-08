"""Pydantic v2 models for the Knowledge Engine subpackage.

Defines all request/response and domain models with full type annotations.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SourceType(str, enum.Enum):
    """Source type enumeration."""

    URL = "url"
    TEXT = "text"


class VerificationStatusEnum(str, enum.Enum):
    """Verification status for claims."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"


class SourceRecord(BaseModel):
    """A source record representing ingested content."""

    id: str
    url: str | None = None
    text_content: str
    source_type: SourceType
    content_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = Field(default_factory=dict)


class SnapshotRecord(BaseModel):
    """A snapshot of a source at a point in time."""

    id: str
    source_id: str
    snapshot_hash: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content: str


class ArtifactRecord(BaseModel):
    """An artifact extracted from a source."""

    id: str
    source_id: str
    extracted_text: str
    extraction_method: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClaimRecord(BaseModel):
    """A claim extracted from an artifact."""

    id: str
    artifact_id: str
    text: str
    score: float = 0.0
    status: VerificationStatusEnum = VerificationStatusEnum.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceSpan(BaseModel):
    """A span of evidence supporting a claim."""

    id: str
    claim_id: str
    source_id: str
    span_text: str
    start_offset: int
    end_offset: int


class ContradictionRecord(BaseModel):
    """A contradiction between two claims."""

    id: str
    claim_id_a: str
    claim_id_b: str
    contradiction_score: float
    description: str


class CoordinateRecord(BaseModel):
    """A deterministic coordinate for content in the Library of Babel."""

    id: str
    content_hash: str
    lineage_hash: str
    semantic_cluster: int
    coordinate_hex: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VerificationRecord(BaseModel):
    """A verification result for a claim."""

    id: str
    claim_id: str
    status: VerificationStatusEnum
    overall_score: float
    verified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditLogRecord(BaseModel):
    """An audit log entry."""

    id: str
    event_type: str
    entity_id: str
    details: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IngestSourceRequest(BaseModel):
    """Request to ingest a source."""

    url: str | None = None
    text: str | None = None
    source_type: SourceType = SourceType.TEXT
    metadata: dict[str, str] = Field(default_factory=dict)


class IngestSourceResponse(BaseModel):
    """Response after ingesting a source."""

    source_id: str
    content_hash: str
    message: str


class ExtractTextResponse(BaseModel):
    """Response after extracting text from an artifact."""

    artifact_id: str
    extracted_text: str
    method: str


class TranslateResponse(BaseModel):
    """Response after translation/stability check."""

    artifact_id: str
    stability_score: float
    translated: bool


class ClaimsResponse(BaseModel):
    """Response containing a list of claims."""

    claims: list[ClaimRecord]
    count: int


class EvidenceLinkResponse(BaseModel):
    """Response containing evidence spans."""

    evidence_spans: list[EvidenceSpan]
    count: int


class ScoreResponse(BaseModel):
    """Response containing a claim score."""

    claim_id: str
    overall_score: float
    status: VerificationStatusEnum


class QueryRequest(BaseModel):
    """Request to query the knowledge engine."""

    query: str
    max_results: int = 10
    min_score: float = 0.0


class QueryResponse(BaseModel):
    """Response containing query results."""

    results: list[ClaimRecord]
    count: int


class ProvenanceResponse(BaseModel):
    """Response containing provenance information for a claim."""

    claim_id: str
    source_id: str
    artifact_id: str
    evidence_spans: list[EvidenceSpan]


class ContradictionsResponse(BaseModel):
    """Response containing contradictions for a claim."""

    claim_id: str
    contradictions: list[ContradictionRecord]
    count: int
