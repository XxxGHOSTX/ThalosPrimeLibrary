"""
Deep Synthesis helpers for Thalos Prime.

Provides a deterministic, structured "Nexus" style response that
decomposes the prompt and maps results to the canonical Library of Babel
endpoints. This is intentionally lightweight and non-AI to keep the
package minimal while offering a consistent interface for downstream
systems.
"""

from collections import Counter
from typing import Dict, List

from . import (
    LIBRARY_OF_BABEL_BASE_URL,
    LIBRARY_OF_BABEL_SEARCH_API,
    LIBRARY_OF_BABEL_SEARCH_URL,
)


def _detect_modalities(prompt: str) -> List[str]:
    """Heuristic modality detection for dynamic feedback."""
    modalities = []
    lowered = prompt.lower()
    if any(k in lowered for k in ["dna", "gene", "protein", "peptide", "genomic"]):
        modalities.append("Genomic")
    if any(k in lowered for k in ["molecule", "chemical", "compound"]):
        modalities.append("Chemical")
    if any(k in lowered for k in ["math", "logic", "axiom", "theorem", "proof"]):
        modalities.append("Logical/Mathematical")
    if any(k in lowered for k in ["story", "narrative", "poem", "text"]):
        modalities.append("Linguistic/Narrative")
    if not modalities:
        modalities.append("General")
    return modalities


def deep_synthesis(prompt: str) -> Dict[str, object]:
    """
    Produce a structured "Nexus Result" for a prompt.

    This is a deterministic scaffold: it performs lightweight semantic
    decomposition and returns multi-dimensional views (physical/chemical,
    logical/mathematical, linguistic/narrative) plus the canonical
    Library of Babel endpoints for downstream retrieval.
    """
    tokens = prompt.split()
    token_counts = Counter(tokens)
    modalities = _detect_modalities(prompt)

    def _block(view: str) -> Dict[str, object]:
        return {
            "view": view,
            "relevance": "Relevant to Input",
            "scope": "Unrestricted",
            "coordinates_hint": {
                "base": LIBRARY_OF_BABEL_BASE_URL,
                "search_ui": LIBRARY_OF_BABEL_SEARCH_URL,
                "search_api": LIBRARY_OF_BABEL_SEARCH_API,
            },
            "summary": f"{view} synthesis derived from prompt semantics.",
        }

    return {
        "semantic_decomposition": {
            "tokens": tokens,
            "token_count": len(tokens),
            "unique_tokens": len(token_counts),
            "modalities": modalities,
        },
        "nexus_result": [
            _block("Physical/Chemical"),
            _block("Logical/Mathematical"),
            _block("Linguistic/Narrative"),
        ],
    }
