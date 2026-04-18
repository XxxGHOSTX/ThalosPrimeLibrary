"""Deterministic peptide candidate generation from text constraints."""

from __future__ import annotations

import heapq
from typing import Any

from thalos_prime.lob_babel_generator import query_to_hex
from thalos_prime.lob_decoder import score_coherence

AMINO_ALPHABET = "ACDEFGHIKLMNPQRSTVWY"


def _hex_to_peptide(hex_str: str, length: int) -> str:
    chars: list[str] = []
    for index in range(length):
        nibble = hex_str[index % len(hex_str)]
        amino_index = int(nibble, 16) % len(AMINO_ALPHABET)
        chars.append(AMINO_ALPHABET[amino_index])
    return "".join(chars)


def search_peptide_constraints(
    text: str,
    length: int = 10,
    max_results: int = 3,
) -> list[dict[str, Any]]:
    """Return deterministic peptide candidates for the input text."""
    seed_hex = query_to_hex(text)
    candidates: list[dict[str, Any]] = []

    for offset in range(max_results):
        augmented = f"{seed_hex}{offset:x}"
        sequence = _hex_to_peptide(augmented, length)
        coherence = score_coherence(sequence, text)
        candidates.append(
            {
                "sequence": sequence,
                "address": f"babel://peptide/{augmented}",
                "score": float(coherence.overall_score),
            },
        )

    return heapq.nlargest(max_results, candidates, key=lambda item: float(item["score"]))
