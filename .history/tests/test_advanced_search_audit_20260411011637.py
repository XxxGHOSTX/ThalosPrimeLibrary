"""Tests for advanced search audit reporting logic."""

from __future__ import annotations

from tools.advanced_search_audit import QueryMeasurement, ScenarioReport, _find_needs


def _report(
    name: str,
    ndcg: float,
    diversity: float,
    novelty: float,
    latency_ms: float,
    remote_pages: int,
) -> ScenarioReport:
    measurement = QueryMeasurement(
        query="q",
        latency_ms=latency_ms,
        ndcg=ndcg,
        diversity=diversity,
        novelty_index=novelty,
        result_count=5,
        remote_pages_federated=remote_pages,
    )
    return ScenarioReport(
        scenario=name,
        avg_latency_ms=latency_ms,
        avg_ndcg=ndcg,
        avg_diversity=diversity,
        avg_novelty_index=novelty,
        avg_result_count=5.0,
        total_remote_pages_federated=remote_pages,
        measurements=[measurement],
    )


def test_find_needs_detects_low_signal_and_remote_gap() -> None:
    baseline = _report("baseline_local", ndcg=1.0, diversity=1.0, novelty=0.99, latency_ms=80.0, remote_pages=0)
    enhanced = _report("enhanced_local", ndcg=1.001, diversity=1.005, novelty=0.995, latency_ms=90.0, remote_pages=0)
    adaptive = _report("adaptive_local", ndcg=1.001, diversity=1.005, novelty=0.995, latency_ms=100.0, remote_pages=0)

    needs = _find_needs([baseline, enhanced, adaptive])

    assert any("Relevance signal remains saturated" in item for item in needs)
    assert any("Diversity gain is minimal" in item for item in needs)
    assert any("Adaptive optimization impact is limited" in item for item in needs)
    assert any("Remote federation benchmark is not represented" in item for item in needs)


def test_find_needs_returns_no_blocking_gaps_when_metrics_are_strong() -> None:
    baseline = _report("baseline_local", ndcg=0.90, diversity=0.70, novelty=0.70, latency_ms=120.0, remote_pages=4)
    enhanced = _report("enhanced_local", ndcg=0.95, diversity=0.80, novelty=0.80, latency_ms=140.0, remote_pages=4)
    adaptive = _report("adaptive_local", ndcg=0.96, diversity=0.83, novelty=0.84, latency_ms=150.0, remote_pages=5)

    needs = _find_needs([baseline, enhanced, adaptive])

    assert needs == ["No immediate blocking gaps detected in the audited local scenarios."]
