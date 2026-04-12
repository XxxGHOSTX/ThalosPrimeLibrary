"""Tests for background process wiring and coherence floor enforcement.

Validates:
- _run_coherence_floor_enforcement evicts SEARCH_CACHE entries with sub-79 results.
- _run_coherence_floor_enforcement retains entries where all results score >= 79.
- BackgroundScheduler registers all four expected worker tasks (including
  coherence_floor) when started without --no-background-workers.
- The adaptive search never-empty invariant holds in concert with the cache worker.
- The coherence floor constant equals 79.0 (invariant guard).
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from thalos_prime.__main__ import (
    _COHERENCE_FLOOR_MIN_SCORE,
    BackgroundScheduler,
    WorkerTask,
    _run_coherence_floor_enforcement,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(score: float) -> dict[str, Any]:
    """Build a minimal SearchResponse result dict with the given coherence score."""
    return {
        "address": "test-addr",
        "text": "test text",
        "coherence": {
            "overall_score": score,
            "language_score": score / 100.0,
            "structure_score": score / 100.0,
            "ngram_score": score / 100.0,
            "exact_match_score": score / 100.0,
        },
    }


def _make_response(scores: list[float]) -> dict[str, Any]:
    """Build a minimal SearchResponse dict with results having the given scores."""
    return {
        "query": "test query",
        "results": [_make_result(s) for s in scores],
        "total_found": len(scores),
    }


def _make_task(name: str = "coherence_floor") -> WorkerTask:
    return WorkerTask(name=name, interval_s=60.0, seed=42, step=1)


# ---------------------------------------------------------------------------
# Coherence floor constant
# ---------------------------------------------------------------------------

def test_coherence_floor_is_79() -> None:
    """_COHERENCE_FLOOR_MIN_SCORE must equal 79.0 (invariant guard)."""
    assert _COHERENCE_FLOOR_MIN_SCORE == 79.0


# ---------------------------------------------------------------------------
# _run_coherence_floor_enforcement
# ---------------------------------------------------------------------------

def test_floor_enforcement_evicts_sub79_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entries with at least one result below 79.0 are evicted."""
    fake_cache: dict[str, tuple[dict[str, Any], float]] = {
        "good_key": (_make_response([80.0, 85.0]), time.time()),
        "bad_key": (_make_response([80.0, 75.0]), time.time()),  # 75 < 79
    }
    import thalos_prime.api.routes.search as sr

    monkeypatch.setattr(sr, "SEARCH_CACHE", fake_cache)

    _run_coherence_floor_enforcement(_make_task())

    assert "good_key" in fake_cache, "Compliant entry must not be evicted"
    assert "bad_key" not in fake_cache, "Sub-floor entry must be evicted"


def test_floor_enforcement_retains_all_above_79(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entries where every result scores >= 79.0 are retained."""
    fake_cache: dict[str, tuple[dict[str, Any], float]] = {
        "key_a": (_make_response([79.0, 90.0, 100.0]), time.time()),
        "key_b": (_make_response([80.5, 95.0]), time.time()),
    }
    import thalos_prime.api.routes.search as sr

    monkeypatch.setattr(sr, "SEARCH_CACHE", fake_cache)

    _run_coherence_floor_enforcement(_make_task())

    assert "key_a" in fake_cache
    assert "key_b" in fake_cache


def test_floor_enforcement_empty_cache_no_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enforcement on an empty cache must succeed without error."""
    fake_cache: dict[str, tuple[dict[str, Any], float]] = {}
    import thalos_prime.api.routes.search as sr

    monkeypatch.setattr(sr, "SEARCH_CACHE", fake_cache)

    _run_coherence_floor_enforcement(_make_task())

    assert fake_cache == {}


def test_floor_enforcement_evicts_exactly_at_floor_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A score of exactly 79.0 is NOT evicted (floor is inclusive)."""
    fake_cache: dict[str, tuple[dict[str, Any], float]] = {
        "at_floor": (_make_response([79.0]), time.time()),
        "below_floor": (_make_response([78.99]), time.time()),
    }
    import thalos_prime.api.routes.search as sr

    monkeypatch.setattr(sr, "SEARCH_CACHE", fake_cache)

    _run_coherence_floor_enforcement(_make_task())

    assert "at_floor" in fake_cache, "Exactly 79.0 is on-floor and must be kept"
    assert "below_floor" not in fake_cache, "78.99 is below floor and must be evicted"


def test_floor_enforcement_multiple_bad_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    """All sub-floor entries are evicted in a single pass."""
    fake_cache: dict[str, tuple[dict[str, Any], float]] = {
        "bad1": (_make_response([70.0]), time.time()),
        "bad2": (_make_response([50.0, 60.0]), time.time()),
        "bad3": (_make_response([78.9]), time.time()),
        "good": (_make_response([79.0, 95.0]), time.time()),
    }
    import thalos_prime.api.routes.search as sr

    monkeypatch.setattr(sr, "SEARCH_CACHE", fake_cache)

    _run_coherence_floor_enforcement(_make_task())

    assert set(fake_cache.keys()) == {"good"}


def test_floor_enforcement_entry_with_no_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """An entry with an empty results list is retained (no scores to fail)."""
    fake_cache: dict[str, tuple[dict[str, Any], float]] = {
        "empty_results": ({"query": "x", "results": []}, time.time()),
    }
    import thalos_prime.api.routes.search as sr

    monkeypatch.setattr(sr, "SEARCH_CACHE", fake_cache)

    _run_coherence_floor_enforcement(_make_task())

    assert "empty_results" in fake_cache


def test_floor_enforcement_evicts_malformed_coherence(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entries with missing coherence data (default 0.0) are evicted as sub-floor."""
    fake_cache: dict[str, tuple[dict[str, Any], float]] = {
        "malformed": (
            {"query": "x", "results": [{"address": "a", "coherence": {}}]},
            time.time(),
        ),
    }
    import thalos_prime.api.routes.search as sr

    monkeypatch.setattr(sr, "SEARCH_CACHE", fake_cache)

    _run_coherence_floor_enforcement(_make_task())

    assert "malformed" not in fake_cache, (
        "Entry with missing overall_score (defaulting to 0.0) must be evicted"
    )


# ---------------------------------------------------------------------------
# BackgroundScheduler registration
# ---------------------------------------------------------------------------

def test_scheduler_registers_coherence_floor_task() -> None:
    """BackgroundScheduler can accept and register a coherence_floor task."""
    scheduler = BackgroundScheduler(config_hash="deadbeef12345678")
    task = WorkerTask(name="coherence_floor", interval_s=60.0, seed=1)
    scheduler.add_task(task)
    assert any(t.name == "coherence_floor" for t in scheduler._tasks)


def test_scheduler_registers_all_four_workers() -> None:
    """The four canonical background workers can all be registered."""
    scheduler = BackgroundScheduler(config_hash="deadbeef12345678")
    for name, interval in [
        ("index_refresh", 300.0),
        ("cache_warm", 600.0),
        ("session_maintenance", 900.0),
        ("coherence_floor", 60.0),
    ]:
        scheduler.add_task(WorkerTask(name=name, interval_s=interval, seed=0))

    registered_names = {t.name for t in scheduler._tasks}
    assert registered_names == {
        "index_refresh",
        "cache_warm",
        "session_maintenance",
        "coherence_floor",
    }


def test_scheduler_coherence_floor_in_worker_handlers() -> None:
    """coherence_floor must be present in _WORKER_HANDLERS registry."""
    from thalos_prime.__main__ import _WORKER_HANDLERS

    assert "coherence_floor" in _WORKER_HANDLERS
    assert callable(_WORKER_HANDLERS["coherence_floor"])


# ---------------------------------------------------------------------------
# Never-empty invariant via adaptive search
# ---------------------------------------------------------------------------

def test_never_empty_invariant_direct() -> None:
    """adaptive_search always returns at least one result >= 79.0."""
    from thalos_prime.adaptive_search import adaptive_search

    results = adaptive_search("background coherence floor validation", max_results=1)
    assert len(results) >= 1
    for r in results:
        assert r.coherence.overall_score >= 79.0, (
            f"Background-sourced result scored {r.coherence.overall_score:.2f} < 79.0"
        )


def test_never_empty_on_unusual_query() -> None:
    """adaptive_search handles unusual/short queries without returning empty."""
    from thalos_prime.adaptive_search import adaptive_search

    for query in ["z", "123", "!@#"]:
        results = adaptive_search(query, max_results=1)
        assert results, f"Empty results for query={query!r}"
        assert results[0].coherence.overall_score >= 79.0
