"""Tests for Library of Sense synthesis components."""

from __future__ import annotations

from thalos_prime.library_of_sense.core.interfaces import (
    QueryContext,
    RetrievalResult,
    SynthesisResult,
)
from thalos_prime.library_of_sense.synthesis.answer_generator import AnswerGenerator
from thalos_prime.library_of_sense.synthesis.conflict_resolution import ConflictResolver
from thalos_prime.library_of_sense.synthesis.knowledge_fusion import KnowledgeFusion
from thalos_prime.library_of_sense.synthesis.verification import ResultVerifier


def _make_result(source: str, content: str, confidence: float) -> RetrievalResult:
    return RetrievalResult(source=source, content=content, confidence=confidence)


# ---------------------------------------------------------------------------
# KnowledgeFusion
# ---------------------------------------------------------------------------


class TestKnowledgeFusion:
    def test_synthesize_empty(self) -> None:
        fusion = KnowledgeFusion()
        ctx = QueryContext()
        result = fusion.synthesize([], ctx)
        assert result.answer == ""
        assert result.confidence == 0.0

    def test_synthesize_single(self) -> None:
        fusion = KnowledgeFusion()
        ctx = QueryContext()
        results = [_make_result("src", "hello world", 0.8)]
        result = fusion.synthesize(results, ctx)
        assert "hello" in result.answer
        assert result.confidence > 0

    def test_synthesize_multiple(self) -> None:
        fusion = KnowledgeFusion()
        ctx = QueryContext()
        results = [
            _make_result("a", "apple is a fruit", 0.9),
            _make_result("b", "banana is yellow", 0.7),
        ]
        result = fusion.synthesize(results, ctx)
        assert len(result.sources) >= 1

    def test_deduplicate_removes_dupes(self) -> None:
        fusion = KnowledgeFusion(dedup_threshold=0.5)
        results = [
            _make_result("a", "the cat sat on the mat", 0.8),
            _make_result("b", "the cat sat on the mat", 0.7),
        ]
        unique = fusion.deduplicate(results)
        assert len(unique) == 1

    def test_deduplicate_no_dupes(self) -> None:
        fusion = KnowledgeFusion()
        results = [
            _make_result("a", "apple is red", 0.8),
            _make_result("b", "sky is blue", 0.7),
        ]
        unique = fusion.deduplicate(results)
        assert len(unique) == 2


# ---------------------------------------------------------------------------
# ConflictResolver
# ---------------------------------------------------------------------------


class TestConflictResolver:
    def test_synthesize_empty(self) -> None:
        resolver = ConflictResolver()
        ctx = QueryContext()
        result = resolver.synthesize([], ctx)
        assert result.answer == ""

    def test_synthesize_non_empty(self) -> None:
        resolver = ConflictResolver()
        ctx = QueryContext()
        results = [
            _make_result("a", "Python is a language", 0.9),
            _make_result("b", "Python is interpreted", 0.7),
        ]
        result = resolver.synthesize(results, ctx)
        assert result.answer != ""
        assert result.confidence > 0

    def test_synthesize_all_empty_content(self) -> None:
        resolver = ConflictResolver()
        ctx = QueryContext()
        results = [_make_result("a", "", 0.5)]
        result = resolver.synthesize(results, ctx)
        assert result.answer == ""


# ---------------------------------------------------------------------------
# ResultVerifier
# ---------------------------------------------------------------------------


class TestResultVerifier:
    def test_verify_empty_answer_invalid(self) -> None:
        verifier = ResultVerifier()
        synthesis = SynthesisResult(answer="", confidence=0.8, sources=[])
        result = verifier.verify(synthesis)
        assert result.valid is False

    def test_verify_low_confidence_invalid(self) -> None:
        verifier = ResultVerifier(min_confidence=0.7)
        r = _make_result("src", "hello world", 0.5)
        synthesis = SynthesisResult(answer="hello world", confidence=0.5, sources=[r])
        result = verifier.verify(synthesis)
        assert result.valid is False

    def test_verify_ungrounded_invalid(self) -> None:
        verifier = ResultVerifier()
        r = _make_result("src", "completely different content", 0.9)
        synthesis = SynthesisResult(
            answer="totally unrelated answer xyz", confidence=0.9, sources=[r]
        )
        result = verifier.verify(synthesis)
        assert result.valid is False

    def test_verify_valid_result(self) -> None:
        verifier = ResultVerifier()
        r = _make_result("src", "Python is a programming language", 0.9)
        synthesis = SynthesisResult(
            answer="Python is a programming language",
            confidence=0.9,
            sources=[r],
        )
        result = verifier.verify(synthesis)
        assert result.valid is True

    def test_verify_and_mark_updates_flag(self) -> None:
        verifier = ResultVerifier()
        r = _make_result("src", "test content here", 0.9)
        synthesis = SynthesisResult(answer="test content here", confidence=0.9, sources=[r])
        marked = verifier.verify_and_mark(synthesis)
        assert marked.verified is True


# ---------------------------------------------------------------------------
# AnswerGenerator
# ---------------------------------------------------------------------------


class TestAnswerGenerator:
    def test_generate_verified_answer(self) -> None:
        gen = AnswerGenerator()
        r = _make_result("src", "test data", 0.9)
        synthesis = SynthesisResult(
            answer="test data", confidence=0.9, sources=[r], verified=True
        )
        ctx = QueryContext()
        answer = gen.generate("test query", synthesis, ctx)
        assert answer.query == "test query"
        assert answer.verified is True
        assert any("verified" in step.lower() for step in answer.reasoning_steps)

    def test_generate_unverified_answer(self) -> None:
        gen = AnswerGenerator()
        synthesis = SynthesisResult(answer="some answer", confidence=0.3, verified=False)
        ctx = QueryContext()
        answer = gen.generate("query", synthesis, ctx)
        assert answer.verified is False
        assert any("not verified" in step.lower() for step in answer.reasoning_steps)
