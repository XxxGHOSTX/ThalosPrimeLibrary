"""Deterministic latent pattern recovery benchmark using the canonical engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from statistics import mean
from typing import Any

from thalos_prime.core.engine import EngineConfig, ThalosEngine
from thalos_prime.lob_babel_generator import address_to_page
from thalos_prime.lob_decoder import score_coherence


@dataclass(frozen=True)
class BenchmarkRow:
    """Per-query comparative benchmark row."""

    query: str
    engine_score: float
    baseline_text_to_address: float
    baseline_sha256_chain: float


def _baseline_scores(query: str) -> tuple[float, float]:
    addr_a = sha256(f"baseline-a:{query}".encode("utf-8")).hexdigest()
    addr_b = sha256(f"baseline-b:{query}".encode("utf-8")).hexdigest()
    score_a = float(score_coherence(address_to_page(addr_a), query).overall_score)
    score_b = float(score_coherence(address_to_page(addr_b), query).overall_score)
    return score_a, score_b


def run_comparative_benchmark(*, seed: int = 2026, perturbation: int = 0) -> dict[str, Any]:
    """Run deterministic comparative benchmark through ``ThalosEngine``."""
    queries = [
        "recover latent linguistic coherence pattern",
        "find deterministic symbolic structure",
        "search comparative semantic stabilization",
    ]
    engine = ThalosEngine()
    rows: list[BenchmarkRow] = []

    for index, query in enumerate(queries):
        config = EngineConfig(
            seed=seed + perturbation + index,
            mode="generative",
            intent_override="search",
            max_candidates=5,
        )
        artifact = engine.run(query, config)
        b1, b2 = _baseline_scores(query)
        rows.append(
            BenchmarkRow(
                query=query,
                engine_score=float(artifact.selected.score),
                baseline_text_to_address=b1,
                baseline_sha256_chain=b2,
            ),
        )

    summary = {
        "engine_mean": mean(row.engine_score for row in rows),
        "baseline_text_to_address_mean": mean(row.baseline_text_to_address for row in rows),
        "baseline_sha256_chain_mean": mean(row.baseline_sha256_chain for row in rows),
    }
    summary["engine_vs_baseline_text_to_address"] = summary["engine_mean"] - summary["baseline_text_to_address_mean"]
    summary["engine_vs_baseline_sha256_chain"] = summary["engine_mean"] - summary["baseline_sha256_chain_mean"]

    return {
        "benchmark": "latent_pattern_recovery",
        "seed": seed,
        "perturbation": perturbation,
        "rows": [asdict(row) for row in rows],
        "summary": summary,
    }
