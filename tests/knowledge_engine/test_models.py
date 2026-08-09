"""Tests for knowledge_engine.models."""

from __future__ import annotations

from thalos_prime.knowledge_engine.models import (
    ArtifactRecord,
    AuditLogRecord,
    ClaimRecord,
    ContradictionRecord,
    CoordinateRecord,
    EvidenceSpan,
    IngestSourceRequest,
    IngestSourceResponse,
    SnapshotRecord,
    SourceRecord,
    SourceType,
    VerificationRecord,
    VerificationStatusEnum,
)


def test_source_record_creation() -> None:
    rec = SourceRecord(
        id="s1",
        text_content="Hello world",
        source_type=SourceType.TEXT,
        content_hash="abc123",
    )
    assert rec.id == "s1"
    assert rec.source_type == SourceType.TEXT
    assert rec.url is None


def test_source_record_with_url() -> None:
    rec = SourceRecord(
        id="s2",
        url="https://example.com",
        text_content="content",
        source_type=SourceType.URL,
        content_hash="def456",
    )
    assert rec.url == "https://example.com"
    assert rec.source_type == SourceType.URL


def test_claim_record_defaults() -> None:
    claim = ClaimRecord(id="c1", artifact_id="a1", text="The sky is blue.")
    assert claim.score == 0.0
    assert claim.status == VerificationStatusEnum.PENDING


def test_verification_status_enum() -> None:
    assert VerificationStatusEnum.PENDING.value == "pending"
    assert VerificationStatusEnum.VERIFIED.value == "verified"
    assert VerificationStatusEnum.REJECTED.value == "rejected"
    assert VerificationStatusEnum.UNCERTAIN.value == "uncertain"


def test_source_type_enum() -> None:
    assert SourceType.URL.value == "url"
    assert SourceType.TEXT.value == "text"


def test_evidence_span() -> None:
    span = EvidenceSpan(
        id="e1", claim_id="c1", source_id="s1",
        span_text="sky is blue", start_offset=4, end_offset=15,
    )
    assert span.start_offset == 4
    assert span.end_offset == 15


def test_contradiction_record() -> None:
    rec = ContradictionRecord(
        id="cr1", claim_id_a="c1", claim_id_b="c2",
        contradiction_score=0.9, description="Contradicts",
    )
    assert rec.contradiction_score == 0.9


def test_coordinate_record() -> None:
    rec = CoordinateRecord(
        id="coord1", content_hash="abc", lineage_hash="def",
        semantic_cluster=0, coordinate_hex="deadbeef",
    )
    assert rec.semantic_cluster == 0


def test_audit_log_record() -> None:
    rec = AuditLogRecord(id="al1", event_type="ingest", entity_id="s1")
    assert rec.event_type == "ingest"


def test_snapshot_record() -> None:
    rec = SnapshotRecord(
        id="sn1", source_id="s1", snapshot_hash="hash1", content="text",
    )
    assert rec.source_id == "s1"


def test_verification_record() -> None:
    rec = VerificationRecord(
        id="v1", claim_id="c1",
        status=VerificationStatusEnum.VERIFIED, overall_score=0.9,
    )
    assert rec.overall_score == 0.9


def test_ingest_source_request_defaults() -> None:
    req = IngestSourceRequest(text="hello world")
    assert req.source_type == SourceType.TEXT
    assert req.metadata == {}


def test_ingest_source_response() -> None:
    resp = IngestSourceResponse(
        source_id="s1", content_hash="abc", message="ok",
    )
    assert resp.source_id == "s1"


def test_artifact_record() -> None:
    rec = ArtifactRecord(
        id="a1", source_id="s1",
        extracted_text="text", extraction_method="plain",
    )
    assert rec.extraction_method == "plain"
