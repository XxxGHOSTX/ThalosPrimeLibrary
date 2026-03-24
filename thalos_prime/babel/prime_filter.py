"""Riemann-Babel Filter — Data Plane: prime index scoring.

Pure data-plane numerical computations for the Riemann-Babel Filter pipeline:
  - Sieve of Eratosthenes for prime generation
  - Primorial index generation (product of first n primes)
  - Prime-gap walking (index sequences anchored to prime gaps)
  - Normalized Shannon entropy scoring of page text
  - Binary-derivative periodicity scoring
  - Composite prime-index scoring combining the above

No lifecycle coordination, no I/O side effects.
All functions are pure and deterministic.

Data Plane boundary: this module performs computational work only.
No control-plane coordination, lifecycle management, or I/O.

State surfaces: none — all functions are stateless.

Checkpoint format: N/A — stateless.

Event log: none — pure data-plane computation.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Weight and scale constants
# ---------------------------------------------------------------------------

_ENTROPY_WEIGHT: float = 0.4
_GAP_WEIGHT: float = 0.3
_PRANK_WEIGHT: float = 0.2
_PERIOD_WEIGHT: float = 0.1
_PRANK_LOG_SCALE: float = 10.0  # log2 scale; saturates at primorial rank ~1023
_MAX_PRIMES_INITIAL: int = 100
_PRIME_GAP_WALK_MIN_STEPS: int = 50

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrimeIndexScore:
    """Scoring result for a single Babel page index.

    Attributes:
        index: The page index (>= 0).
        primorial_rank: Number of primes whose product (primorial) does not
            exceed *index*; zero when ``index < 2``.
        prime_gap_score: Normalised score from prime-gap walk alignment
            in ``[0.0, 1.0]``.
        entropy_score: Normalised Shannon entropy of the page text
            in ``[0.0, 1.0]``.
        composite_periodicity_score: Binary-derivative periodicity score
            in ``[0.0, 1.0]``.
        combined: Weighted composite score in ``[0.0, 1.0]``.
    """

    index: int
    primorial_rank: int
    prime_gap_score: float
    entropy_score: float
    composite_periodicity_score: float
    combined: float


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sieve_of_eratosthenes(limit: int) -> list[int]:
    """Return all primes up to and including *limit*.

    Uses the classical Sieve of Eratosthenes algorithm.

    Args:
        limit: Upper bound (inclusive) for prime search.

    Returns:
        Sorted list of all primes ``p`` where ``2 <= p <= limit``.

    Raises:
        ValueError: If *limit* is less than 2.
    """
    if limit < 2:
        msg = f"limit must be >= 2, got {limit!r}"
        raise ValueError(msg)

    is_prime = bytearray([1]) * (limit + 1)
    is_prime[0] = 0
    is_prime[1] = 0

    for i in range(2, math.isqrt(limit) + 1):
        if is_prime[i]:
            is_prime[i * i :: i] = bytearray(len(is_prime[i * i :: i]))

    return [i for i, flag in enumerate(is_prime) if flag]


def _shannon_entropy(text: str) -> float:
    """Compute normalised Shannon entropy of *text* in ``[0.0, 1.0]``.

    The raw Shannon entropy is divided by ``log2(alphabet_size)`` so the
    result is always in the unit interval.  A uniform distribution over the
    observed alphabet yields 1.0; a single repeated character yields 0.0.

    Args:
        text: Input string to analyse.

    Returns:
        Normalised entropy in ``[0.0, 1.0]``.
    """
    if not text:
        return 0.0

    counts = Counter(text)
    alphabet_size = len(counts)
    if alphabet_size <= 1:
        return 0.0

    total = len(text)
    raw_entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    max_entropy = math.log2(alphabet_size)
    return raw_entropy / max_entropy


def _binary_derivative_score(text: str) -> float:
    """Compute a periodicity score from first-order character differences.

    Calculates the sequence of character-code differences between consecutive
    characters.  Counts runs of equal consecutive differences (periodicity
    indicator) and normalises to ``[0.0, 1.0]``.

    Args:
        text: Input string to analyse.

    Returns:
        Periodicity score in ``[0.0, 1.0]``.  Higher values indicate
        more periodic (repetitive-structure) text.
    """
    if len(text) < 2:
        return 0.0

    diffs = [ord(text[i + 1]) - ord(text[i]) for i in range(len(text) - 1)]
    n_diffs = len(diffs)
    if n_diffs <= 1:
        return 0.0

    repeats = sum(1 for i in range(n_diffs - 1) if diffs[i] == diffs[i + 1])
    return repeats / (n_diffs - 1)


def _primorial_rank(index: int) -> int:
    """Return the primorial rank for *index*.

    The primorial rank is the largest ``n`` such that the product of the
    first ``n`` primes (the n-th primorial) is ``<= index``.  Returns 0
    if ``index < 2``.

    Args:
        index: Non-negative integer page index.

    Returns:
        Primorial rank (>= 0).
    """
    if index < 2:
        return 0

    # Generate enough primes; primorial(15) ~ 6.1e17, which covers any
    # reasonable 64-bit page index.
    limit = max(_MAX_PRIMES_INITIAL, 200)
    primes = _sieve_of_eratosthenes(limit)

    product = 1
    rank = 0
    for p in primes:
        next_product = product * p
        if next_product > index:
            break
        product = next_product
        rank += 1

    return rank


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_primorial_indices(limit: int) -> list[int]:
    """Return all primorials up to and including *limit*.

    A primorial is the product of the first ``n`` primes.  The sequence
    starts ``[2, 6, 30, 210, 2310, …]``.

    Args:
        limit: Maximum primorial value to include (inclusive).

    Returns:
        Sorted list of primorials ``<= limit``.

    Raises:
        ValueError: If *limit* is less than 1.
    """
    if limit < 1:
        msg = f"limit must be >= 1, got {limit!r}"
        raise ValueError(msg)

    primes = _sieve_of_eratosthenes(max(2, limit))
    result: list[int] = []
    product = 1
    for p in primes:
        product *= p
        if product > limit:
            break
        result.append(product)

    return result


def prime_gap_walk(start: int, steps: int) -> list[int]:
    """Walk through a sequence of indices anchored to prime gaps.

    Constructs a sequence where each step advances by the gap between
    consecutive primes.  The first prime gap is ``3 - 2 = 1``, then
    ``5 - 3 = 2``, ``7 - 5 = 2``, ``11 - 7 = 4``, and so on.

    ``prime_gap_walk(0, 0)`` returns ``[0]``.

    Args:
        start: Starting index (>= 0).
        steps: Number of steps to walk (>= 0).  The returned list has
            ``steps + 1`` elements.

    Returns:
        List of ``steps + 1`` non-decreasing integer indices.

    Raises:
        ValueError: If *start* < 0 or *steps* < 0.
    """
    if start < 0:
        msg = f"start must be >= 0, got {start!r}"
        raise ValueError(msg)
    if steps < 0:
        msg = f"steps must be >= 0, got {steps!r}"
        raise ValueError(msg)

    if steps == 0:
        return [start]

    # We need at least (steps + 1) primes so we can compute (steps) gaps.
    limit = max(30, (steps + 2) * 20)
    primes = _sieve_of_eratosthenes(limit)

    # Extend sieve if the initial estimate was too small
    while len(primes) <= steps:
        limit *= 2
        primes = _sieve_of_eratosthenes(limit)

    positions: list[int] = [start]
    for i in range(steps):
        gap = primes[i + 1] - primes[i]
        positions.append(positions[-1] + gap)

    return positions


def score_index(index: int, page_text: str) -> PrimeIndexScore:
    """Compute a composite prime-index score for a Babel page.

    Combines four metrics via fixed weights:

    - Shannon entropy of the page text (weight 0.4)
    - Prime-gap walk alignment score (weight 0.3)
    - Logarithmically scaled primorial rank (weight 0.2)
    - Binary-derivative periodicity score (weight 0.1)

    Args:
        index: Non-negative Babel page index.
        page_text: The text content of the page.

    Returns:
        A ``PrimeIndexScore`` containing all sub-scores and the combined
        weighted composite.

    Raises:
        ValueError: If *index* is less than 0.
    """
    if index < 0:
        msg = f"index must be >= 0, got {index!r}"
        raise ValueError(msg)

    prank = _primorial_rank(index)
    ent = _shannon_entropy(page_text)
    period = _binary_derivative_score(page_text)

    # Prime-gap walk score: proximity to walk anchored at 0
    steps = max(_PRIME_GAP_WALK_MIN_STEPS, prank + 10)
    walk = prime_gap_walk(0, steps=steps)

    if index in walk:
        pos = walk.index(index)
        gap_score = 1.0 - (pos / len(walk))
    else:
        max_walk_value = walk[-1]
        min_dist = min(abs(index - w) for w in walk)
        gap_score = max(0.0, 1.0 - min_dist / (max_walk_value + 1))

    prank_score = min(1.0, math.log2(prank + 1) / _PRANK_LOG_SCALE)

    combined = (
        ent * _ENTROPY_WEIGHT
        + gap_score * _GAP_WEIGHT
        + prank_score * _PRANK_WEIGHT
        + period * _PERIOD_WEIGHT
    )

    return PrimeIndexScore(
        index=index,
        primorial_rank=prank,
        prime_gap_score=gap_score,
        entropy_score=ent,
        composite_periodicity_score=period,
        combined=combined,
    )


__all__: list[str] = [
    "PrimeIndexScore",
    "generate_primorial_indices",
    "prime_gap_walk",
    "score_index",
]
