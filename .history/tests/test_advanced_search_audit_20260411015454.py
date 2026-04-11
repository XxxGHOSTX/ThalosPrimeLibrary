"""Tests for advanced search audit reporting logic."""

from __future__ import annotations

from tools.advanced_search_audit import QueryMeasurement, ScenarioReport, _find_needs


def _report(
    name: str,
    metrics: tuple[float, float, float, float],
    remote_pages: int,
) -> ScenarioReport:
    ndcg, diversity, novelty, latency_ms = metrics
    measurement = QueryMeasurement(
        query="q",
        latency_ms=latency_ms,
        ndcg=ndcg,
        diversity=diversity,
        novelty_index=novelty,
        result_count=5,
        remote_pages_federated=remote_pages,
        local_build_ms=10.0,
        remote_fetch_ms=5.0,
        rerank_ms=1.0,
    )
    return ScenarioReport(
        scenario=name,
        avg_latency_ms=latency_ms,
        avg_ndcg=ndcg,
        avg_diversity=diversity,
        avg_novelty_index=novelty,
        avg_relevance=ndcg,
        avg_result_count=5.0,
        total_remote_pages_federated=remote_pages,
        measurements=[measurement],
    )


def test_find_needs_detects_low_signal_and_remote_gap() -> None:
    baseline = _report("baseline_local", metrics=(1.0, 1.0, 0.99, 80.0), remote_pages=0)
    enhanced = _report("enhanced_local", metrics=(1.001, 1.005, 0.995, 90.0), remote_pages=0)
    adaptive = _report("adaptive_local", metrics=(1.001, 1.005, 0.995, 100.0), remote_pages=0)

    needs = _find_needs([baseline, enhanced, adaptive])

    assert any("Relevance signal remains saturated" in item for item in needs)
    assert any("Diversity gain is minimal" in item for item in needs)
    assert any("Adaptive optimization impact is limited" in item for item in needs)
    assert any("Remote federation benchmark is not represented" in item for item in needs)


def test_find_needs_returns_no_blocking_gaps_when_metrics_are_strong() -> None:
    baseline = _report("baseline_local", metrics=(0.90, 0.70, 0.70, 120.0), remote_pages=4)
    enhanced = _report("enhanced_local", metrics=(0.95, 0.80, 0.80, 140.0), remote_pages=4)
    adaptive = _report("adaptive_local", metrics=(0.96, 0.83, 0.84, 150.0), remote_pages=5)

    needs = _find_needs([baseline, enhanced, adaptive])

    assert needs == ["No immediate blocking gaps detected in the audited local scenarios."]
