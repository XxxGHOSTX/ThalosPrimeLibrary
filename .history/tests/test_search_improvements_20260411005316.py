"""Tests for enhanced search relevance and diversity behavior."""

from __future__ import annotations

from thalos_prime.api.routes.search import _diversify_results, _expand_query_variants
from thalos_prime.models.api_models import (
    AddressInfo,
    CoherenceInfo,
    ConfidenceLevel,
    PageResult,
    ProvenanceInfo,
)


def _make_page_result(text: str, score: float, combined_score: float) -> PageResult:
    return PageResult(
        address=AddressInfo(
            hex_address="abc123",
            wall=None,
            shelf=None,
            volume=None,
            page=None,
            url=None,
        ),
        text=text,
        snippet=text[:120],
        normalized_text=None,
        coherence=CoherenceInfo(
            overall_score=score,
            language_score=score,
            structure_score=score,
            ngram_score=score,
            exact_match_score=score,
            confidence_level=ConfidenceLevel.MEDIUM,
            metrics={"combined_score": combined_score},
        ),
        provenance=ProvenanceInfo(
            address="abc123",
            source="local",
            query="test",
            timestamp=0.0,
            normalized=False,
            llm_provider=None,
        ),
    )


def test_expand_query_variants_is_deterministic() -> None:
    query = "Deterministic linguistic coherence in library search"
    first = _expand_query_variants(query)
    second = _expand_query_variants(query)

    assert first == second
    assert first
    assert first[0] == query


def test_diversify_results_prefers_novel_second_choice() -> None:
    very_similar_a = _make_page_result(
        "linguistic coherence language structure analysis repeated repeated repeated",
        score=90.0,
        combined_score=90.0,
    )
    very_similar_b = _make_page_result(
        "linguistic coherence language structure analysis repeated repeated alternate",
        score=88.0,
        combined_score=88.0,
    )
    different_topic = _make_page_result(
        "symbolic constraint solving optimization graph traversal deterministic planning",
        score=82.0,
        combined_score=82.0,
    )

    reranked = _diversify_results(
        [very_similar_a, very_similar_b, different_topic],
        max_results=2,
        diversity_lambda=0.6,
    )

    assert len(reranked) == 2
    assert reranked[0].text == very_similar_a.text
    assert reranked[1].text == different_topic.text
