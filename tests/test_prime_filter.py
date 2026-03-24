"""Tests for thalos_prime.babel.prime_filter."""

from __future__ import annotations

import pytest

from thalos_prime.babel.prime_filter import (
    PrimeIndexScore,
    _binary_derivative_score,
    _primorial_rank,
    _shannon_entropy,
    _sieve_of_eratosthenes,
    generate_primorial_indices,
    prime_gap_walk,
    score_index,
)

# ---------------------------------------------------------------------------
# _sieve_of_eratosthenes
# ---------------------------------------------------------------------------


def test_sieve_basic() -> None:
    assert _sieve_of_eratosthenes(10) == [2, 3, 5, 7]


def test_sieve_limit_2() -> None:
    assert _sieve_of_eratosthenes(2) == [2]


def test_sieve_limit_3() -> None:
    assert _sieve_of_eratosthenes(3) == [2, 3]


def test_sieve_raises_for_limit_below_2() -> None:
    with pytest.raises(ValueError):
        _sieve_of_eratosthenes(1)


def test_sieve_larger() -> None:
    primes = _sieve_of_eratosthenes(30)
    assert primes == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]


# ---------------------------------------------------------------------------
# generate_primorial_indices
# ---------------------------------------------------------------------------


def test_generate_primorial_indices_basic() -> None:
    result = generate_primorial_indices(210)
    assert result[:4] == [2, 6, 30, 210]


def test_generate_primorial_indices_empty_limit() -> None:
    assert generate_primorial_indices(1) == []


def test_generate_primorial_indices_limit_2() -> None:
    assert generate_primorial_indices(2) == [2]


def test_generate_primorial_indices_raises_below_1() -> None:
    with pytest.raises(ValueError):
        generate_primorial_indices(0)


def test_generate_primorial_indices_all_lte_limit() -> None:
    limit = 500
    result = generate_primorial_indices(limit)
    assert all(v <= limit for v in result)


# ---------------------------------------------------------------------------
# prime_gap_walk
# ---------------------------------------------------------------------------


def test_prime_gap_walk_zero_steps() -> None:
    assert prime_gap_walk(5, 0) == [5]
    assert prime_gap_walk(0, 0) == [0]


def test_prime_gap_walk_basic_increasing() -> None:
    walk = prime_gap_walk(0, 5)
    assert len(walk) == 6
    for i in range(len(walk) - 1):
        assert walk[i] < walk[i + 1]


def test_prime_gap_walk_deterministic() -> None:
    w1 = prime_gap_walk(0, 10)
    w2 = prime_gap_walk(0, 10)
    assert w1 == w2


def test_prime_gap_walk_negative_start_raises() -> None:
    with pytest.raises(ValueError):
        prime_gap_walk(-1, 5)


def test_prime_gap_walk_negative_steps_raises() -> None:
    with pytest.raises(ValueError):
        prime_gap_walk(0, -1)


def test_prime_gap_walk_nonzero_start() -> None:
    walk = prime_gap_walk(100, 5)
    assert walk[0] == 100
    assert len(walk) == 6
    for i in range(len(walk) - 1):
        assert walk[i] < walk[i + 1]


def test_prime_gap_walk_first_step_is_one() -> None:
    # First prime gap: 3 - 2 = 1
    walk = prime_gap_walk(0, 1)
    assert walk == [0, 1]


# ---------------------------------------------------------------------------
# _shannon_entropy
# ---------------------------------------------------------------------------


def test_shannon_entropy_uniform() -> None:
    # All identical chars → entropy near 0
    assert _shannon_entropy("aaaaaa") == pytest.approx(0.0, abs=1e-9)


def test_shannon_entropy_empty() -> None:
    assert _shannon_entropy("") == pytest.approx(0.0, abs=1e-9)


def test_shannon_entropy_varied() -> None:
    text = "abcdefghijklmnopqrstuvwxyz"
    entropy = _shannon_entropy(text)
    assert entropy > 0.9  # near-maximum for uniform distribution


def test_shannon_entropy_two_chars() -> None:
    text = "ab" * 50  # perfectly balanced two-char alphabet
    entropy = _shannon_entropy(text)
    assert entropy == pytest.approx(1.0, abs=1e-6)


def test_shannon_entropy_in_range() -> None:
    for text in ["hello world", "aaabbb", "xyz", "123"]:
        e = _shannon_entropy(text)
        assert 0.0 <= e <= 1.0


# ---------------------------------------------------------------------------
# _binary_derivative_score
# ---------------------------------------------------------------------------


def test_binary_derivative_score_empty_returns_zero() -> None:
    assert _binary_derivative_score("") == pytest.approx(0.0)
    assert _binary_derivative_score("a") == pytest.approx(0.0)


def test_binary_derivative_score_arithmetic_sequence() -> None:
    # "bdfh..." — each char is +2 from previous → all diffs equal → max periodicity
    text = "".join(chr(ord("a") + 2 * i) for i in range(20))
    score = _binary_derivative_score(text)
    assert score == pytest.approx(1.0, abs=1e-9)


def test_binary_derivative_score_in_range() -> None:
    for text in ["hello world", "abcxyz", "aaaa", "random text here!"]:
        score = _binary_derivative_score(text)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# _primorial_rank
# ---------------------------------------------------------------------------


def test_primorial_rank_zero_for_small_index() -> None:
    assert _primorial_rank(0) == 0
    assert _primorial_rank(1) == 0


def test_primorial_rank_index_2() -> None:
    # primorial(1) = 2 ≤ 2; primorial(2) = 6 > 2
    assert _primorial_rank(2) == 1


def test_primorial_rank_index_6() -> None:
    # primorial(2) = 6 ≤ 6; primorial(3) = 30 > 6
    assert _primorial_rank(6) == 2


def test_primorial_rank_index_30() -> None:
    # primorial(3) = 30 ≤ 30; primorial(4) = 210 > 30
    assert _primorial_rank(30) == 3


def test_primorial_rank_index_100() -> None:
    # primorial(3) = 30 ≤ 100; primorial(4) = 210 > 100
    assert _primorial_rank(100) == 3


# ---------------------------------------------------------------------------
# score_index
# ---------------------------------------------------------------------------


def test_score_index_returns_correct_type() -> None:
    result = score_index(0, "hello world")
    assert isinstance(result, PrimeIndexScore)


def test_score_index_combined_in_range() -> None:
    for idx in [0, 1, 10, 100, 1000]:
        result = score_index(idx, "test page text " * 10)
        assert 0.0 <= result.combined <= 1.0


def test_score_index_invalid_negative() -> None:
    with pytest.raises(ValueError):
        score_index(-1, "text")


def test_score_index_deterministic() -> None:
    text = "the quick brown fox jumps over the lazy dog"
    r1 = score_index(42, text)
    r2 = score_index(42, text)
    assert r1 == r2


def test_score_index_all_fields_present() -> None:
    result = score_index(5, "sample text")
    assert result.index == 5
    assert isinstance(result.primorial_rank, int)
    assert 0.0 <= result.prime_gap_score <= 1.0
    assert 0.0 <= result.entropy_score <= 1.0
    assert 0.0 <= result.composite_periodicity_score <= 1.0
    assert 0.0 <= result.combined <= 1.0


def test_score_index_entropy_zero_for_uniform_text() -> None:
    # All same character → very low entropy_score
    result = score_index(0, "a" * 100)
    assert result.entropy_score == pytest.approx(0.0, abs=1e-9)
