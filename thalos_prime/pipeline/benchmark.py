"""Deterministic candidate benchmarking stage."""

from __future__ import annotations

from hashlib import sha256
from statistics import mean

from thalos_prime.lob_babel_generator import address_to_page, text_to_address
from thalos_prime.lob_decoder import score_coherence


def _baseline_scores(input_text: str) -> dict[str, float]:
    direct_address = text_to_address(input_text)
    hash_address = sha256(f"baseline:{input_text}".encode("utf-8")).hexdigest()

    direct_page = address_to_page(direct_address)
    hash_page = address_to_page(hash_address)
    direct_score = float(score_coherence(direct_page, input_text).overall_score)
    hash_score = float(score_coherence(hash_page, input_text).overall_score)

    return {
        "text_to_address": direct_score,
        "sha256_chain": hash_score,
        "mean": mean([direct_score, hash_score]),
    }


def score_candidates(
    candidates: list[dict[str, object]],
    *,
    input_text: str,
) -> tuple[list[dict[str, object]], dict[str, float]]:
    """Compute deterministic candidate and purity scores versus baselines."""
    baselines = _baseline_scores(input_text)
    scored: list[dict[str, object]] = []

    for candidate in candidates:
        coherence = float(candidate["coherence_score"])
        constraint = float(candidate["constraint_score"])
        purity = max(0.0, min(100.0, (coherence * 0.7) + (constraint * 0.3)))
        score = max(0.0, min(100.0, (coherence * 0.75) + (constraint * 0.25)))
        scored.append(
            {
                **candidate,
                "purity_score": purity,
                "score": score,
            },
        )

    scored.sort(key=lambda item: (float(item["score"]), str(item["candidate_id"])), reverse=True)
    selected_score = float(scored[0]["score"]) if scored else 0.0

    purity_metrics = {
        "selected_score": selected_score,
        "baseline_text_to_address": baselines["text_to_address"],
        "baseline_sha256_chain": baselines["sha256_chain"],
        "baseline_mean": baselines["mean"],
        "purity_functional": selected_score - baselines["mean"],
    }
    return scored, purity_metrics
