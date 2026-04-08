"""Tests for knowledge_engine.scoring."""

from __future__ import annotations

import pytest

from thalos_prime.knowledge_engine.models import (
    ClaimRecord,
    ContradictionRecord,
    EvidenceSpan,
    SourceRecord,
    SourceType,
    VerificationStatusEnum,
)
from thalos_prime.knowledge_engine.scoring.scorer import VerificationScorer


def _make_source(source_type: SourceType = SourceType.TEXT) -> SourceRecord:
    return SourceRecord(
        id="s1", text_content="content",
        source_type=source_type, content_hash="abc",
    )


def _make_claim() -> ClaimRecord:
    return ClaimRecord(id="c1", artifact_id="a1", text="The sky is blue.")


def _make_span() -> EvidenceSpan:
    return EvidenceSpan(
        id="e1", claim_id="c1", source_id="s1",
        span_text="The sky is blue.", start_offset=0, end_offset=16,
    )


def test_scorer_lifecycle() -> None:
    scorer = VerificationScorer()
    scorer.initialize()
    scorer.validate()
    scorer.operate()
    scorer.reconcile()
    cp = scorer.checkpoint()
    assert cp["component"] == "VerificationScorer"
    scorer.terminate()


def test_score_claim_with_evidence() -> None:
    scorer = VerificationScorer()
    scorer.initialize()
    claim = _make_claim()
    source = _make_source(SourceType.TEXT)
    spans = [_make_span()]
    score = scorer.score_claim(claim, spans, [], source, 1.0)
    assert 0.0 <= score <= 1.0
    assert score > 0.5
    scorer.terminate()


def test_score_claim_without_evidence() -> None:
    scorer = VerificationScorer()
    scorer.initialize()
    claim = _make_claim()
    source = _make_source(SourceType.TEXT)
    score = scorer.score_claim(claim, [], [], source, 1.0)
    assert 0.0 <= score <= 1.0
    scorer.terminate()


def test_score_claim_with_contradiction() -> None:
    scorer = VerificationScorer()
    scorer.initialize()
    claim = _make_claim()
    source = _make_source(SourceType.TEXT)
    spans = [_make_span()]
    contradiction = ContradictionRecord(
        id="cr1", claim_id_a="c1", claim_id_b="c2",
        contradiction_score=1.0, description="test",
    )
    score = scorer.score_claim(claim, spans, [contradiction], source, 1.0)
    assert 0.0 <= score <= 1.0
    scorer.terminate()


def test_determine_status_verified() -> None:
    scorer = VerificationScorer()
    scorer.initialize()
    status = scorer.determine_status(0.9)
    assert status == VerificationStatusEnum.VERIFIED
    scorer.terminate()


def test_determine_status_uncertain() -> None:
    scorer = VerificationScorer()
    scorer.initialize()
    status = scorer.determine_status(0.5)
    assert status == VerificationStatusEnum.UNCERTAIN
    scorer.terminate()


def test_determine_status_rejected() -> None:
    scorer = VerificationScorer()
    scorer.initialize()
    status = scorer.determine_status(0.1)
    assert status == VerificationStatusEnum.REJECTED
    scorer.terminate()


def test_score_source_trust_url() -> None:
    scorer = VerificationScorer()
    scorer.initialize()
    source = _make_source(SourceType.URL)
    trust = scorer.score_source_trust(source)
    assert trust == 0.8
    scorer.terminate()


def test_score_source_trust_text() -> None:
    scorer = VerificationScorer()
    scorer.initialize()
    source = _make_source(SourceType.TEXT)
    trust = scorer.score_source_trust(source)
    assert trust == 0.6
    scorer.terminate()


def test_scorer_not_initialized_raises() -> None:
    scorer = VerificationScorer()
    claim = _make_claim()
    source = _make_source()
    with pytest.raises(RuntimeError, match="not initialized"):
        scorer.score_claim(claim, [], [], source, 1.0)


def test_scorer_validate_not_initialized() -> None:
    scorer = VerificationScorer()
    with pytest.raises(RuntimeError, match="not initialized"):
        scorer.validate()
