from typing import Any, Dict, List

from src.lob_babel_generator import query_to_hex
from src.lob_decoder import score_coherence


AMINO_ALPHABET = "ACDEFGHIKLMNPQRSTVWY"


def _hex_to_peptide(hex_str: str, length: int) -> str:
    """
    Deterministically map a hex string to a peptide by wrapping over the hex seed;
    repetition encodes the Babel-style coordinate.
    """
    chars = []
    for i in range(length):
        h = hex_str[i % len(hex_str)]
        idx = int(h, 16) % len(AMINO_ALPHABET)
        chars.append(AMINO_ALPHABET[idx])
    return "".join(chars)


def search_peptide_constraints(text: str, length: int = 10, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Prototype permutation searcher: maps constraint text to deterministic peptide
    sequences (Babel-style coordinates) and scores them for coherence.
    """
    seed_hex = query_to_hex(text)
    candidates: List[Dict[str, Any]] = []
    for offset in range(max_results):
        augmented = f"{seed_hex}{offset:x}"
        sequence = _hex_to_peptide(augmented, length)
        score = score_coherence(sequence, text)
        candidates.append(
            {
                "sequence": sequence,
                "address": f"babel://peptide/{augmented}",
                "score": score,
            }
        )

    # Keep top scores; heap avoids unnecessary sort if max_results grows.
    import heapq

    return heapq.nlargest(max_results, candidates, key=lambda r: r["score"])
