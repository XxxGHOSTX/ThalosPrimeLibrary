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


def test_run_benchmark_returns_expected_scenarios() -> None:
    aggregates = run_benchmark(
        query_suite=["deterministic query"],
        max_results=2,
        threshold=10.0,
    )

    assert set(aggregates) == {
        "thalos_pipeline",
        "direct_hash_baseline",
        "randomish_baseline",
    }
    assert aggregates["thalos_pipeline"].avg_best_score >= 0.0


def test_to_payload_contains_comparison_fields() -> None:
    aggregates = run_benchmark(
        query_suite=["deterministic query"],
        max_results=2,
        threshold=10.0,
    )
    payload = _to_payload(aggregates=aggregates, threshold=10.0, max_results=2)

    comparisons = payload["comparisons"]
    assert isinstance(comparisons, dict)
    assert "thalos_vs_direct_hash_win_rate" in comparisons
    assert "thalos_vs_randomish_win_rate" in comparisons
