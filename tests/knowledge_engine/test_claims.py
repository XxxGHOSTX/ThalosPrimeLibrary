"""Tests for knowledge_engine.claims."""

from __future__ import annotations

import pytest

from thalos_prime.knowledge_engine.claims.extractor import ClaimExtractor
from thalos_prime.knowledge_engine.claims.linker import EvidenceLinker
from thalos_prime.knowledge_engine.models import (
    ArtifactRecord,
    ClaimRecord,
    SourceRecord,
    SourceType,
    VerificationStatusEnum,
)


def test_claim_extractor_lifecycle() -> None:
    extractor = ClaimExtractor()
    extractor.initialize()
    extractor.validate()
    extractor.operate()
    extractor.reconcile()
    cp = extractor.checkpoint()
    assert cp["component"] == "ClaimExtractor"
    extractor.terminate()


def test_extract_claims_basic() -> None:
    extractor = ClaimExtractor()
    extractor.initialize()
    artifact = ArtifactRecord(
        id="a1", source_id="s1",
        extracted_text="The sky is blue. Water is wet. Fire is hot.",
        extraction_method="plain",
    )
    claims = extractor.extract_claims(artifact)
    assert len(claims) >= 2
    for claim in claims:
        assert claim.artifact_id == "a1"
        assert claim.status == VerificationStatusEnum.PENDING
    extractor.terminate()


def test_extract_claims_filters_short() -> None:
    extractor = ClaimExtractor()
    extractor.initialize()
    artifact = ArtifactRecord(
        id="a1", source_id="s1",
        extracted_text="Hi. This is a longer sentence that should be extracted.",
        extraction_method="plain",
    )
    claims = extractor.extract_claims(artifact)
    texts = [c.text for c in claims]
    assert "Hi" not in texts
    extractor.terminate()


def test_extract_claims_not_initialized_raises() -> None:
    extractor = ClaimExtractor()
    artifact = ArtifactRecord(
        id="a1", source_id="s1", extracted_text="text.", extraction_method="plain",
    )
    with pytest.raises(RuntimeError, match="not initialized"):
        extractor.extract_claims(artifact)


def test_claim_extractor_validate_not_initialized() -> None:
    extractor = ClaimExtractor()
    with pytest.raises(RuntimeError, match="not initialized"):
        extractor.validate()


def test_claim_extractor_reconcile_not_initialized() -> None:
    extractor = ClaimExtractor()
    with pytest.raises(RuntimeError, match="not initialized"):
        extractor.reconcile()


def test_evidence_linker_lifecycle() -> None:
    linker = EvidenceLinker()
    linker.initialize()
    linker.validate()
    linker.operate()
    linker.reconcile()
    cp = linker.checkpoint()
    assert cp["component"] == "EvidenceLinker"
    linker.terminate()


def test_evidence_linker_finds_span() -> None:
    linker = EvidenceLinker()
    linker.initialize()
    source = SourceRecord(
        id="s1",
        text_content="The sky is blue. The sky is always blue.",
        source_type=SourceType.TEXT,
        content_hash="abc",
    )
    claim = ClaimRecord(id="c1", artifact_id="a1", text="The sky is blue")
    spans = linker.link(claim, source)
    assert len(spans) >= 1
    assert spans[0].claim_id == "c1"
    assert spans[0].source_id == "s1"
    linker.terminate()


def test_evidence_linker_no_match() -> None:
    linker = EvidenceLinker()
    linker.initialize()
    source = SourceRecord(
        id="s1", text_content="Nothing relevant here.",
        source_type=SourceType.TEXT, content_hash="abc",
    )
    claim = ClaimRecord(id="c1", artifact_id="a1", text="The sky is blue")
    spans = linker.link(claim, source)
    assert spans == []
    linker.terminate()


def test_evidence_linker_not_initialized_raises() -> None:
    linker = EvidenceLinker()
    source = SourceRecord(
        id="s1", text_content="text", source_type=SourceType.TEXT, content_hash="abc",
    )
    claim = ClaimRecord(id="c1", artifact_id="a1", text="text")
    with pytest.raises(RuntimeError, match="not initialized"):
        linker.link(claim, source)
