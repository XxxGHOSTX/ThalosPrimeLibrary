"""Tests for thalos_runtime.core.prime_pipeline."""

from __future__ import annotations

import pytest

from thalos_nexus.recipes import DataSignature
from thalos_prime.babel.prime_filter import PrimeIndexScore
from thalos_runtime.core.prime_pipeline import (
    CandidatePage,
    _classify_chars,
    _normalized_shannon_entropy,
    find_prime_aligned_candidates,
)

# ---------------------------------------------------------------------------
# _classify_chars
# ---------------------------------------------------------------------------


def test_classify_chars_alpha() -> None:
    assert _classify_chars("hello") == frozenset({"alpha"})


def test_classify_chars_digit() -> None:
    assert _classify_chars("123") == frozenset({"digit"})


def test_classify_chars_space() -> None:
    assert _classify_chars("   ") == frozenset({"space"})


def test_classify_chars_mixed() -> None:
    classes = _classify_chars("hello world 123!")
    assert "alpha" in classes
    assert "space" in classes
    assert "digit" in classes
    assert "punct" in classes


def test_classify_chars_empty() -> None:
    assert _classify_chars("") == frozenset()


def test_classify_chars_punct() -> None:
    classes = _classify_chars(".,!?")
    assert "punct" in classes


# ---------------------------------------------------------------------------
# _normalized_shannon_entropy
# ---------------------------------------------------------------------------


def test_normalized_shannon_entropy_empty() -> None:
    assert _normalized_shannon_entropy("") == pytest.approx(0.0)


def test_normalized_shannon_entropy_uniform() -> None:
    assert _normalized_shannon_entropy("aaaa") == pytest.approx(0.0, abs=1e-9)


def test_normalized_shannon_entropy_varied() -> None:
    entropy = _normalized_shannon_entropy("abcdefgh")
    assert entropy > 0.9


def test_normalized_shannon_entropy_in_range() -> None:
    for text in ["hello", "world", "abc xyz 123"]:
        e = _normalized_shannon_entropy(text)
        assert 0.0 <= e <= 1.0


# ---------------------------------------------------------------------------
# find_prime_aligned_candidates — validation
# ---------------------------------------------------------------------------


def test_find_prime_aligned_candidates_empty_query_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        find_prime_aligned_candidates("")


def test_find_prime_aligned_candidates_invalid_max_zero_raises() -> None:
    with pytest.raises(ValueError):
        find_prime_aligned_candidates("hello", max_candidates=0)


def test_find_prime_aligned_candidates_invalid_max_too_large_raises() -> None:
    with pytest.raises(ValueError):
        find_prime_aligned_candidates("hello", max_candidates=257)


# ---------------------------------------------------------------------------
# find_prime_aligned_candidates — results
# ---------------------------------------------------------------------------


def test_find_prime_aligned_candidates_basic() -> None:
    results = find_prime_aligned_candidates("hello", max_candidates=4)
    assert isinstance(results, list)
    # The enumerator may return fewer than max_candidates
    assert len(results) <= 4


def test_find_prime_aligned_candidates_returns_candidate_pages() -> None:
    results = find_prime_aligned_candidates("test", max_candidates=2)
    for page in results:
        assert isinstance(page, CandidatePage)


def test_find_prime_aligned_candidates_sorted_by_score() -> None:
    results = find_prime_aligned_candidates("mathematics", max_candidates=8)
    scores = [p.prime_score.combined for p in results]
    assert scores == sorted(scores, reverse=True)


def test_candidate_page_has_signature() -> None:
    results = find_prime_aligned_candidates("cipher", max_candidates=2)
    for page in results:
        assert isinstance(page.signature, DataSignature)


def test_candidate_page_signature_fields() -> None:
    results = find_prime_aligned_candidates("babel", max_candidates=2)
    for page in results:
        sig = page.signature
        assert isinstance(sig.length, int)
        assert isinstance(sig.char_classes, frozenset)
        assert isinstance(sig.entropy, float)
        assert 0.0 <= sig.prime_index_score <= 1.0


def test_candidate_page_prime_score_type() -> None:
    results = find_prime_aligned_candidates("prime", max_candidates=2)
    for page in results:
        assert isinstance(page.prime_score, PrimeIndexScore)


def test_candidate_page_address_is_string() -> None:
    results = find_prime_aligned_candidates("address", max_candidates=2)
    for page in results:
        assert isinstance(page.address, str)
        assert len(page.address) > 0


def test_candidate_page_text_is_string() -> None:
    results = find_prime_aligned_candidates("text", max_candidates=2)
    for page in results:
        assert isinstance(page.text, str)
        assert len(page.text) > 0


def test_find_prime_aligned_candidates_deterministic() -> None:
    r1 = find_prime_aligned_candidates("determinism", max_candidates=4)
    r2 = find_prime_aligned_candidates("determinism", max_candidates=4)
    assert len(r1) == len(r2)
    for p1, p2 in zip(r1, r2, strict=True):
        assert p1.address == p2.address
        assert p1.prime_score.combined == pytest.approx(p2.prime_score.combined)


def test_find_prime_aligned_candidates_max_candidates_one() -> None:
    results = find_prime_aligned_candidates("single", max_candidates=1)
    assert len(results) <= 1


def test_find_prime_aligned_candidates_score_in_range() -> None:
    results = find_prime_aligned_candidates("range", max_candidates=4)
    for page in results:
        assert 0.0 <= page.prime_score.combined <= 1.0
