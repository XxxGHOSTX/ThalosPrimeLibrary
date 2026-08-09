"""Deterministic candidate generation stage."""

from __future__ import annotations

from hashlib import sha256

from thalos_prime.adaptive_search import adaptive_search
from thalos_prime.lob_babel_enumerator import enumerate_addresses
from thalos_prime.lob_babel_generator import address_to_page
from thalos_prime.lob_decoder import score_coherence

_ALLOWED_MODES = {"local", "hybrid", "generative", "remote"}


def _as_float(value: object) -> float:
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    msg = f"Unsupported numeric value type: {type(value)!r}"
    raise TypeError(msg)


def generate_candidates(
    input_text: str,
    *,
    max_candidates: int,
    mode: str,
    cycle_index: int,
) -> list[dict[str, object]]:
    """Generate deterministic candidates for solver/benchmark stages."""
    effective_mode = mode if mode in _ALLOWED_MODES else "hybrid"

    if effective_mode == "generative":
        adaptive = adaptive_search(input_text, max_results=max_candidates)
        return [
            {
                "candidate_id": f"gen-{idx}",
                "address": item.address,
                "text": item.text,
                "source": f"adaptive_stage_{item.stage}",
                "coherence_score": float(item.coherence.overall_score),
                "metadata": {"stage": item.stage, "seed": item.seed, "cycle": cycle_index},
            }
            for idx, item in enumerate(adaptive)
        ]

    # Local/hybrid path: enumerate addresses and score generated pages.
    addresses = enumerate_addresses(input_text, max_results=max_candidates * 2, depth=2)
    candidates: list[dict[str, object]] = []
    for idx, info in enumerate(addresses[: max_candidates * 2]):
        address = str(info["address"])
        page = address_to_page(address)
        coherence = score_coherence(page, input_text)
        candidates.append(
            {
                "candidate_id": f"loc-{idx}",
                "address": address,
                "text": page,
                "source": effective_mode,
                "coherence_score": float(coherence.overall_score),
                "metadata": {"depth": info.get("depth", 0), "cycle": cycle_index},
            },
        )

    if not candidates:
        fallback_address = sha256(f"{input_text}\0{cycle_index}".encode()).hexdigest()
        page = address_to_page(fallback_address)
        coherence = score_coherence(page, input_text)
        candidates.append(
            {
                "candidate_id": "fallback-0",
                "address": fallback_address,
                "text": page,
                "source": "fallback",
                "coherence_score": float(coherence.overall_score),
                "metadata": {"cycle": cycle_index},
            },
        )

    candidates.sort(
        key=lambda item: (
            _as_float(item["coherence_score"]),
            str(item["address"]),
            str(item["candidate_id"]),
        ),
        reverse=True,
    )
    return candidates[:max_candidates]
