"""Deterministic internal research synthesis stage."""

from __future__ import annotations

from thalos_prime.lob_babel_enumerator import enumerate_addresses
from thalos_prime.lob_babel_generator import address_to_page
from thalos_prime.lob_decoder import score_coherence


def _as_float(value: object) -> float:
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    msg = f"Unsupported numeric value type: {type(value)!r}"
    raise TypeError(msg)


def synthesize_research(input_text: str, *, max_results: int) -> dict[str, object]:
    """Build deterministic local research notes without remote calls."""
    addresses = enumerate_addresses(input_text, max_results=max_results, depth=2)
    notes: list[dict[str, object]] = []

    for address_info in addresses[:max_results]:
        address = str(address_info["address"])
        page = address_to_page(address)
        coherence = score_coherence(page, input_text)
        notes.append(
            {
                "address": address,
                "score": float(coherence.overall_score),
                "snippet": page[:200],
            },
        )

    notes.sort(key=lambda item: (_as_float(item["score"]), str(item["address"])), reverse=True)
    return {
        "method": "local_research_synthesis",
        "addresses_considered": len(addresses),
        "notes": notes,
    }
