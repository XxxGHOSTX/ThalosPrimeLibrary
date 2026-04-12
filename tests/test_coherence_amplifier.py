"""Tests for the CoherenceAmplifier (SLCA framework).

Validates:
- All four SLCA operators (QSAP, FWLI, SPR, BRA) contribute correctly.
- amplify_to_threshold() guarantees overall_score >= 79.0 on any input.
- Amplification is deterministic given identical (text, query, seed).
- amplify_to_threshold() works on empty text, random text, and Library pages.
"""

from __future__ import annotations

import pytest

from thalos_prime.coherence_amplifier import (
    CoherenceAmplifier,
    amplify_to_threshold,
    seed_from_address,
)
from thalos_prime.lob_babel_generator import BabelGenerator
from thalos_prime.lob_decoder import BabelDecoder

_DECODER = BabelDecoder()
_AMP = CoherenceAmplifier()
_GEN = BabelGenerator()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_amplify_deterministic_same_seed() -> None:
    """Same (text, query, seed) always produces identical amplified text."""
    text = "some low coherence text here"
    query = "test determinism"
    result1 = amplify_to_threshold(text, query, seed=42)
    result2 = amplify_to_threshold(text, query, seed=42)
    assert result1 == result2


def test_amplify_different_seeds_different_output() -> None:
    """Different seeds produce different amplified texts."""
    text = "some text"
    query = "query"
    result1 = amplify_to_threshold(text, query, seed=1)
    result2 = amplify_to_threshold(text, query, seed=99999)
    # BRA uses seed to rotate phrases, so outputs differ
    assert result1 != result2


# ---------------------------------------------------------------------------
# Threshold guarantee: >= 79.0 on all inputs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(("query", "seed"), [
    ("hello world", 42),
    ("antimicrobial peptide structure discovery", 0),
    ("ThalosPrime deterministic coherence", 99999),
    ("knowledge graph semantic alignment", 314159),
    ("hybrid retrieval generation consistency", 7),
    ("single word", 1),
])
def test_amplify_score_above_79_for_parameterized_queries(query: str, seed: int) -> None:
    """amplify_to_threshold produces text scoring >= 79.0 for varied queries."""
    text = "random low quality base text"
    amplified = amplify_to_threshold(text, query, seed=seed)
    cs = _DECODER.score_coherence(amplified, query)
    assert cs.overall_score >= 79.0, (
        f"query={query!r} seed={seed} scored {cs.overall_score:.2f} < 79.0"
    )


def test_amplify_empty_text_still_scores_above_79() -> None:
    """Amplification on an empty base text still guarantees >= 79.0."""
    amplified = amplify_to_threshold("", "what is the meaning of this", seed=0)
    cs = _DECODER.score_coherence(amplified, "what is the meaning of this")
    assert cs.overall_score >= 79.0


def test_amplify_on_random_library_page_scores_above_79() -> None:
    """Amplification on a raw low-coherence Library page guarantees >= 79.0."""
    page = _GEN.address_to_page("deadbeef00112233")  # random-looking page (~19%)
    query = "library of babel coherence test"
    amplified = amplify_to_threshold(page, query, seed=seed_from_address("deadbeef00112233"))
    cs = _DECODER.score_coherence(amplified, query)
    assert cs.overall_score >= 79.0, (
        f"Amplified Library page scored {cs.overall_score:.2f} < 79.0"
    )


def test_amplify_batch_all_above_79() -> None:
    """All ten queries produce amplified text scoring >= 79.0."""
    queries = [
        "deterministic language coherence retrieval",
        "symbolic constraint solver reasoning quality",
        "knowledge graph semantic alignment",
        "novel evidence extraction from noisy text",
        "hybrid retrieval generation consistency",
        "epistemic validation pipeline",
        "belief state management",
        "edge native inference",
        "lifecycle protocol enforcement",
        "checkpoint and restore contracts",
    ]
    for i, query in enumerate(queries):
        amplified = amplify_to_threshold("base", query, seed=i * 7)
        cs = _DECODER.score_coherence(amplified, query)
        assert cs.overall_score >= 79.0, (
            f"Query {query!r} scored {cs.overall_score:.2f} < 79.0"
        )


# ---------------------------------------------------------------------------
# QSAP: query must be present in output
# ---------------------------------------------------------------------------

def test_qsap_query_appears_in_output() -> None:
    """The full query must appear in the amplified text (QSAP invariant)."""
    query = "antimicrobial peptide discovery"
    amplified = amplify_to_threshold("noise", query, seed=5)
    assert query.lower() in amplified.lower(), (
        "QSAP must embed full query in amplified text"
    )


# ---------------------------------------------------------------------------
# seed_from_address helper
# ---------------------------------------------------------------------------

def test_seed_from_address_deterministic() -> None:
    """seed_from_address is stable across calls."""
    addr = "abc123def456"
    assert seed_from_address(addr) == seed_from_address(addr)


def test_seed_from_address_different_for_different_inputs() -> None:
    """Different addresses produce different seeds (with overwhelmingly high probability)."""
    assert seed_from_address("aaaa") != seed_from_address("bbbb")
