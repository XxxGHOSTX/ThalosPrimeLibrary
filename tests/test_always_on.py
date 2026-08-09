"""Tests for always-on automatic background behaviors.

Validates:
- SearchRequest defaults to always-on for adaptive optimization,
  query expansion, and diversity reranking (no manual flags required).
- Background worker handlers execute without raising errors.
- New workers (coherence_floor_enforcer, benchmark_reporter, audit_health_check)
  are registered in _WORKER_HANDLERS.
- WorkerTask step increments are deterministic.
"""

from __future__ import annotations

import pytest

from thalos_prime.models.api_models import SearchRequest

# ---------------------------------------------------------------------------
# Always-on defaults: no manual flags required
# ---------------------------------------------------------------------------

def test_enable_adaptive_optimization_is_true_by_default() -> None:
    """enable_adaptive_optimization must default to True — always-on."""
    req = SearchRequest(query="test")
    assert req.enable_adaptive_optimization is True, (
        "enable_adaptive_optimization must default to True so adaptive search "
        "runs automatically without any manual flag."
    )


def test_enable_query_expansion_is_true_by_default() -> None:
    """enable_query_expansion must default to True — always-on."""
    req = SearchRequest(query="test")
    assert req.enable_query_expansion is True, (
        "enable_query_expansion must default to True for automatic always-on behavior."
    )


def test_enable_diversity_rerank_is_true_by_default() -> None:
    """enable_diversity_rerank must default to True — always-on."""
    req = SearchRequest(query="test")
    assert req.enable_diversity_rerank is True, (
        "enable_diversity_rerank must default to True for automatic always-on behavior."
    )


@pytest.mark.parametrize(
    "flag",
    ["enable_adaptive_optimization", "enable_query_expansion", "enable_diversity_rerank"],
)
def test_explicit_false_still_accepted(flag: str) -> None:
    """Callers can still explicitly disable individual features if needed."""
    if flag == "enable_adaptive_optimization":
        req = SearchRequest(query="test", enable_adaptive_optimization=False)
    elif flag == "enable_query_expansion":
        req = SearchRequest(query="test", enable_query_expansion=False)
    elif flag == "enable_diversity_rerank":
        req = SearchRequest(query="test", enable_diversity_rerank=False)
    else:
        pytest.fail(f"Unexpected flag value: {flag!r}")
        return  # unreachable — satisfies mypy
    assert getattr(req, flag) is False


# ---------------------------------------------------------------------------
# Background worker registry completeness
# ---------------------------------------------------------------------------

def test_all_always_on_workers_registered() -> None:
    """All six always-on worker handlers must be registered in _WORKER_HANDLERS."""
    from thalos_prime.__main__ import _WORKER_HANDLERS

    expected = {
        "index_refresh",
        "cache_warm",
        "session_maintenance",
        "coherence_floor_enforcer",
        "benchmark_reporter",
        "audit_health_check",
    }
    missing = expected - set(_WORKER_HANDLERS.keys())
    assert not missing, (
        f"Missing always-on worker handlers: {missing!r}. "
        "All background workers must be registered so they run automatically."
    )


def test_worker_handlers_are_callable() -> None:
    """Every registered handler must be callable."""
    from thalos_prime.__main__ import _WORKER_HANDLERS

    for name, handler in _WORKER_HANDLERS.items():
        assert callable(handler), f"Handler for worker {name!r} is not callable."


# ---------------------------------------------------------------------------
# WorkerTask determinism
# ---------------------------------------------------------------------------

def test_worker_task_step_increments() -> None:
    """WorkerTask.step increments correctly across multiple calls."""
    from thalos_prime.__main__ import WorkerTask

    task = WorkerTask(name="test_task", interval_s=1.0, seed=12345)
    assert task.step == 0
    task.step += 1
    assert task.step == 1
    task.step += 1
    assert task.step == 2


def test_worker_task_seed_is_preserved() -> None:
    """WorkerTask retains the seed it was initialised with."""
    from thalos_prime.__main__ import WorkerTask

    seed = 0xDEADBEEF
    task = WorkerTask(name="seeded_task", interval_s=60.0, seed=seed)
    assert task.seed == seed


# ---------------------------------------------------------------------------
# Coherence floor enforcer: smoke test
# ---------------------------------------------------------------------------

def test_coherence_floor_enforcer_clears_sub_floor_entries() -> None:
    """_run_coherence_floor_enforcer evicts SearchResponse payloads below floor.

    Uses SearchResponse.model_dump()-shaped payloads — the actual cache schema —
    where scores live at results[].coherence.overall_score, not at a top-level key.
    """
    from thalos_prime.__main__ import WorkerTask, _run_coherence_floor_enforcer
    from thalos_prime.api.routes.search import SEARCH_CACHE

    def _make_payload(overall_score: float) -> dict[str, object]:
        """Return a minimal SearchResponse.model_dump()-shaped payload."""
        return {
            "query": "test",
            "results": [
                {
                    "address": {"hex_address": "abc123", "url": "http://example.com"},
                    "text": "x" * 3200,
                    "coherence": {"overall_score": overall_score, "confidence_level": "high"},
                    "provenance": {"address": "abc123", "source": "local", "timestamp": 0.0},
                }
            ],
            "total_found": 1,
            "mode": "hybrid",
            "cached": False,
            "metadata": {},
        }

    SEARCH_CACHE["floor_sr_below"] = (_make_payload(50.0), 0.0)
    SEARCH_CACHE["floor_sr_above"] = (_make_payload(90.0), 0.0)
    # Entry with no results list — min score defaults to 0.0 so it IS evicted.
    SEARCH_CACHE["floor_sr_empty_results"] = ({"query": "test", "results": []}, 0.0)

    task = WorkerTask(name="coherence_floor_enforcer", interval_s=120.0, seed=1)
    _run_coherence_floor_enforcer(task)

    assert "floor_sr_below" not in SEARCH_CACHE, "Below-floor entry should be evicted."
    assert "floor_sr_above" in SEARCH_CACHE, "Above-floor entry should be retained."
    assert "floor_sr_empty_results" not in SEARCH_CACHE, (
        "Entry with empty results (min score = 0.0) should be evicted."
    )

    # Cleanup
    SEARCH_CACHE.pop("floor_sr_above", None)


# ---------------------------------------------------------------------------
# Benchmark reporter: smoke test (no network, deterministic)
# ---------------------------------------------------------------------------

def test_benchmark_reporter_runs_without_error() -> None:
    """_run_benchmark_reporter executes without raising."""
    from thalos_prime.__main__ import WorkerTask, _run_benchmark_reporter

    task = WorkerTask(name="benchmark_reporter", interval_s=1800.0, seed=42)
    _run_benchmark_reporter(task)  # Must not raise


# ---------------------------------------------------------------------------
# Audit health check: smoke test
# ---------------------------------------------------------------------------

def test_audit_health_check_runs_without_error() -> None:
    """_run_audit_health_check executes without raising."""
    from thalos_prime.__main__ import WorkerTask, _run_audit_health_check

    task = WorkerTask(name="audit_health_check", interval_s=300.0, seed=7)
    _run_audit_health_check(task)  # Must not raise
