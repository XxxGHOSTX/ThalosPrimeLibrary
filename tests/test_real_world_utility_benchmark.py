"""Tests for deterministic real-world utility benchmark tooling."""

from __future__ import annotations

from tools.real_world_utility_benchmark import (
    _deterministic_hex,
    _to_payload,
    run_benchmark,
)


def test_deterministic_hex_stable() -> None:
    first = _deterministic_hex("query", 3)
    second = _deterministic_hex("query", 3)
    assert first == second
    assert len(first) == 64


def test_run_benchmark_thalos_scores_above_79() -> None:
    """Thalos pipeline must score >= 79 on the benchmark threshold."""
    aggregates = run_benchmark(
        query_suite=["deterministic query"],
        max_results=2,
        threshold=79.0,
    )

    assert set(aggregates) == {
        "thalos_pipeline",
        "direct_hash_baseline",
        "randomish_baseline",
    }
    # Thalos pipeline uses the GenerativeEngine corpus — all results score >= 79.
    assert aggregates["thalos_pipeline"].avg_best_score >= 79.0
    assert aggregates["thalos_pipeline"].avg_hit_rate == 1.0

    # Baselines use random Library pages — scores are low (< 79%).
    assert aggregates["direct_hash_baseline"].avg_best_score < 79.0
    assert aggregates["randomish_baseline"].avg_best_score < 79.0


def test_run_benchmark_thalos_outperforms_baselines() -> None:
    """Thalos avg_best_score must strictly exceed both baseline avg_best_scores."""
    aggregates = run_benchmark(
        query_suite=["knowledge graph semantic alignment"],
        max_results=3,
        threshold=79.0,
    )
    thalos_best = aggregates["thalos_pipeline"].avg_best_score
    direct_best = aggregates["direct_hash_baseline"].avg_best_score
    random_best = aggregates["randomish_baseline"].avg_best_score
    assert thalos_best > direct_best, (
        f"Thalos ({thalos_best:.1f}) must exceed direct_hash ({direct_best:.1f})"
    )
    assert thalos_best > random_best, (
        f"Thalos ({thalos_best:.1f}) must exceed randomish ({random_best:.1f})"
    )


def test_to_payload_contains_comparison_fields() -> None:
    aggregates = run_benchmark(
        query_suite=["deterministic query"],
        max_results=2,
        threshold=79.0,
    )
    payload = _to_payload(aggregates=aggregates, threshold=79.0, max_results=2)

    comparisons = payload["comparisons"]
    assert isinstance(comparisons, dict)
    assert "thalos_vs_direct_hash_win_rate" in comparisons
    assert "thalos_vs_randomish_win_rate" in comparisons
    # Thalos should achieve perfect win rate against both baselines.
    assert float(comparisons["thalos_vs_direct_hash_win_rate"]) == 1.0
    assert float(comparisons["thalos_vs_randomish_win_rate"]) == 1.0
