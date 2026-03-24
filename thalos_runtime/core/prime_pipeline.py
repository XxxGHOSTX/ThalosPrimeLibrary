"""Prime Pipeline — Control Plane orchestrator for Riemann-Babel Filter.

Takes a query, enumerates candidate Babel addresses via BabelEnumerator,
generates page text via BabelGenerator, scores each page with the prime
filter, builds DataSignature metadata, and returns ranked CandidatePage
instances ready for the RecipeEngine.

Control Plane / Data Plane separation:
- Control Plane (this module): orchestrates address enumeration, page
  generation, scoring, and signature construction. Coordinates between
  thalos_nexus.recipes.DataSignature (control contract) and the data-
  plane computations in thalos_prime.babel.prime_filter.
- Data Plane (prime_filter.py, lob_babel_generator.py,
  lob_babel_enumerator.py): pure numerical and text computation.

State surfaces:
    _GENERATOR: BabelGenerator — module-level singleton (stateless).
    _ENUMERATOR: BabelEnumerator — module-level singleton (stateless).

Checkpoint format: N/A — stateless pipeline. Inputs are full replay state.

Event log: none — deterministic function with no state transitions.
"""

from __future__ import annotations

import math
import string
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from thalos_nexus.recipes import DataSignature
from thalos_prime.babel.prime_filter import score_index
from thalos_prime.lob_babel_enumerator import BabelEnumerator
from thalos_prime.lob_babel_generator import BabelGenerator

if TYPE_CHECKING:
    from thalos_prime.babel.prime_filter import PrimeIndexScore

# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

_MIN_MAX_CANDIDATES: int = 1
_MAX_MAX_CANDIDATES: int = 256

# ---------------------------------------------------------------------------
# Module-level singletons (stateless; safe to share)
# ---------------------------------------------------------------------------

_GENERATOR: BabelGenerator = BabelGenerator()
_ENUMERATOR: BabelEnumerator = BabelEnumerator()

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidatePage:
    """A Babel page candidate produced by the prime pipeline.

    Attributes:
        index: Zero-based enumeration index within this pipeline run.
        address: The hexadecimal Babel address used to generate the page.
        text: The 3200-character page text generated from *address*.
        prime_score: Composite prime-index scoring result from the
            Riemann-Babel Filter data plane.
        signature: Structural and statistical metadata derived from *text*
            and *prime_score* for use by the ``RecipeEngine``.
    """

    index: int
    address: str
    text: str
    prime_score: PrimeIndexScore
    signature: DataSignature


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_PUNCT_SET: frozenset[str] = frozenset(string.punctuation)


def _classify_chars(text: str) -> frozenset[str]:
    """Classify the character types present in *text*.

    Returns a frozenset of zero or more labels drawn from
    ``{"alpha", "digit", "space", "punct", "other"}``.

    Args:
        text: Input string to classify.

    Returns:
        frozenset of class-name strings for the character types found.
    """
    classes: set[str] = set()
    for ch in text:
        if ch.isalpha():
            classes.add("alpha")
        elif ch.isdigit():
            classes.add("digit")
        elif ch.isspace():
            classes.add("space")
        elif ch in _PUNCT_SET:
            classes.add("punct")
        else:
            classes.add("other")
    return frozenset(classes)


def _normalized_shannon_entropy(text: str) -> float:
    """Compute normalised Shannon entropy of *text* in ``[0.0, 1.0]``.

    Normalises raw entropy by ``log2(alphabet_size)`` so a uniform
    distribution returns 1.0 and a constant string returns 0.0.

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


def _build_signature(text: str, prime_score: PrimeIndexScore) -> DataSignature:
    """Construct a ``DataSignature`` from page text and its prime-index score.

    Args:
        text: The full page text from the Babel generator.
        prime_score: The ``PrimeIndexScore`` already computed for this page.

    Returns:
        A ``DataSignature`` capturing structural and statistical metadata.
    """
    has_whitespace = (
        " " in text or "\t" in text or "\n" in text or "\r" in text
    )
    return DataSignature(
        length=len(text),
        char_classes=_classify_chars(text),
        has_whitespace=has_whitespace,
        entropy=_normalized_shannon_entropy(text),
        language_hint=None,
        likely_cipher=None,
        encoding_layers=(),
        prime_index_score=prime_score.combined,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_prime_aligned_candidates(
    query: str,
    *,
    max_candidates: int = 32,
) -> list[CandidatePage]:
    """Enumerate, generate, score, and rank Babel page candidates for *query*.

    1. Uses ``BabelEnumerator`` to generate up to *max_candidates* candidate
       hexadecimal addresses from the query.
    2. Uses ``BabelGenerator`` to materialise each address into page text.
    3. Scores each page with the Riemann-Babel Filter
       (``thalos_prime.babel.prime_filter.score_index``).
    4. Builds a ``DataSignature`` for each page.
    5. Returns all pages sorted by ``prime_score.combined`` descending.

    Args:
        query: Non-empty input string to map to candidate Babel addresses.
        max_candidates: Maximum number of candidates to produce;
            must be in ``[1, 256]``.

    Returns:
        List of ``CandidatePage`` instances sorted by
        ``prime_score.combined`` descending (highest-scoring first).

    Raises:
        ValueError: If *query* is empty.
        ValueError: If *max_candidates* is not in ``[1, 256]``.
    """
    if not query:
        msg = "query must not be empty"
        raise ValueError(msg)
    if not (_MIN_MAX_CANDIDATES <= max_candidates <= _MAX_MAX_CANDIDATES):
        msg = (
            f"max_candidates must be in [{_MIN_MAX_CANDIDATES}, {_MAX_MAX_CANDIDATES}],"
            f" got {max_candidates!r}"
        )
        raise ValueError(msg)

    raw_candidates = _ENUMERATOR.enumerate_addresses(query, max_results=max_candidates)

    pages: list[CandidatePage] = []
    for raw in raw_candidates:
        address = str(raw["address"])
        text = _GENERATOR.address_to_page(address)
        # Derive a deterministic page index from the first 8 hex characters of
        # the address (= a 32-bit integer drawn from the SHA-256 digest produced
        # by BabelEnumerator).  This yields a stable, address-specific integer
        # for prime-index scoring rather than the loop's enumeration counter.
        hex_prefix = address[:8].ljust(8, "0")
        page_index = int(hex_prefix, 16)
        prime_score = score_index(page_index, text)
        signature = _build_signature(text, prime_score)
        pages.append(
            CandidatePage(
                index=page_index,
                address=address,
                text=text,
                prime_score=prime_score,
                signature=signature,
            )
        )

    pages.sort(key=lambda p: p.prime_score.combined, reverse=True)
    return pages


__all__: list[str] = [
    "CandidatePage",
    "find_prime_aligned_candidates",
]
