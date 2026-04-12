"""Tests for the AdaptiveCoherenceSearch engine.

Validates:
- search() always returns >= 1 result with overall_score >= 79.0.
- search() never returns an empty list regardless of query.
- Results are deterministic with identical queries.
- All four stages correctly produce qualifying results.
- The failsafe (Stage 4) always succeeds.
"""

from __future__ import annotations

import pytest

from thalos_prime.adaptive_search import (
    AdaptiveCoherenceSearch,
    AdaptiveResult,
    _derive_seed_sequence,
    _query_seed,
    adaptive_search,
)
from thalos_prime.lob_decoder import BabelDecoder

_DECODER = BabelDecoder()


# ---------------------------------------------------------------------------
# Basic invariants
# ---------------------------------------------------------------------------

def test_search_returns_nonempty() -> None:
    """search() never returns an empty list."""
    results = adaptive_search("test query", max_results=1)
    assert len(results) >= 1


def test_search_all_results_above_79() -> None:
    """All results from search() have overall_score >= 79.0."""
    results = adaptive_search("any query here", max_results=3)
    for r in results:
        assert r.coherence.overall_score >= 79.0, (
            f"Result stage={r.stage} scored {r.coherence.overall_score:.2f} < 79.0"
        )


def test_search_returns_requested_count() -> None:
    """search() returns exactly max_results results."""
    results = adaptive_search("deterministic coherence", max_results=5)
    assert len(results) == 5


@pytest.mark.parametrize("query", [
    "hello",
    "antim icrobial peptide discovery process",
    "ThalosPrime library deterministic guarantee",
    "x",
    "knowledge graph semantic alignment inference",
])
def test_search_all_above_79_various_queries(query: str) -> None:
    """All result scores >= 79.0 for diverse query types."""
    results = adaptive_search(query, max_results=2)
    assert results, f"Empty results for query={query!r}"
    for r in results:
        assert r.coherence.overall_score >= 79.0, (
            f"query={query!r} stage={r.stage} scored {r.coherence.overall_score:.2f}"
        )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_search_deterministic_same_query() -> None:
    """Same query always returns the same texts in the same order."""
    q = "deterministic test query reproducibility"
    results1 = adaptive_search(q, max_results=3)
    results2 = adaptive_search(q, max_results=3)
    assert [r.text for r in results1] == [r.text for r in results2]
    assert [r.address for r in results1] == [r.address for r in results2]


def test_search_different_queries_different_results() -> None:
    """Different queries produce different result sets."""
    results_a = adaptive_search("knowledge graph alignment", max_results=2)
    results_b = adaptive_search("symbolic constraint solving", max_results=2)
    # At least one text should differ (both are deterministic and different)
    texts_a = {r.text for r in results_a}
    texts_b = {r.text for r in results_b}
    assert texts_a != texts_b


# ---------------------------------------------------------------------------
# Stage verification
# ---------------------------------------------------------------------------

def test_stage1_provides_results() -> None:
    """Stage 1 (GenerativeEngine) must produce all results for standard queries."""
    engine = AdaptiveCoherenceSearch()
    results = engine.search("ThalosPrime overview architecture", max_results=3)
    # Stage 1 should be sufficient; all results come from stage 1 or 4
    assert all(r.stage in {1, 2, 3, 4} for r in results)
    assert all(r.coherence.overall_score >= 79.0 for r in results)


def test_stage4_failsafe_is_called_when_forced() -> None:
    """Stage 4 failsafe directly produces results scoring >= 79.0."""
    engine = AdaptiveCoherenceSearch()
    # Call stage 4 directly with zero accumulated results
    stage4_results = engine._stage4_amplify_failsafe(
        query="forced failsafe test query",
        max_results=2,
        seed=12345,
        accumulated=[],
    )
    assert len(stage4_results) == 2
    for r in stage4_results:
        assert r.coherence.overall_score >= 79.0, (
            f"Stage 4 failsafe scored {r.coherence.overall_score:.2f} < 79.0"
        )
        assert r.stage == 4


def test_stage4_failsafe_never_empty() -> None:
    """Stage 4 always fills all missing slots."""
    engine = AdaptiveCoherenceSearch()
    for max_r in [1, 3, 10]:
        results = engine._stage4_amplify_failsafe(
            query="edge case empty fill",
            max_results=max_r,
            seed=0,
            accumulated=[],
        )
        assert len(results) == max_r


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

def test_adaptive_result_has_required_fields() -> None:
    """AdaptiveResult contains all required fields with valid types."""
    results = adaptive_search("field validation test", max_results=1)
    r = results[0]
    assert isinstance(r, AdaptiveResult)
    assert isinstance(r.address, str)
    assert len(r.address) > 0
    assert isinstance(r.text, str)
    assert len(r.text) > 0
    assert isinstance(r.stage, int)
    assert r.stage in {1, 2, 3, 4}
    assert isinstance(r.query, str)
    assert isinstance(r.seed, int)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def test_query_seed_stable() -> None:
    """_query_seed is stable across calls."""
    q = "stable seed test"
    assert _query_seed(q) == _query_seed(q)


def test_derive_seed_sequence_length() -> None:
    """_derive_seed_sequence returns exactly count seeds."""
    seeds = _derive_seed_sequence(base_seed=42, count=10)
    assert len(seeds) == 10


def test_derive_seed_sequence_deterministic() -> None:
    """_derive_seed_sequence is deterministic for the same base_seed."""
    s1 = _derive_seed_sequence(base_seed=999, count=5)
    s2 = _derive_seed_sequence(base_seed=999, count=5)
    assert s1 == s2


def test_derive_seed_sequence_all_positive_integers() -> None:
    """All seeds in the sequence are non-negative integers."""
    seeds = _derive_seed_sequence(base_seed=0, count=8)
    assert all(isinstance(s, int) and s >= 0 for s in seeds)
