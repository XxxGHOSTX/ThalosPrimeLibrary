"""Tests for the AutonomousOrchestrator and companion helpers.

Covers:
- AutonomousOrchestrator lifecycle: initialize, validate, operate,
  reconcile, checkpoint, terminate.
- WorkerSpec / WorkerMetrics data classes.
- get_orchestrator / start_orchestrator singleton helpers.
- OrchestratorError typed exception.
- _execute_safely wrapping behaviour.
"""

from __future__ import annotations

import threading
import time

import pytest

from thalos_prime.autonomous.orchestrator import (
    AutonomousOrchestrator,
    OrchestratorError,
    WorkerMetrics,
    WorkerSpec,
    _execute_safely,
    _run_constraint_solving,
    _run_performance_metrics,
    _run_session_maintenance,
    get_orchestrator,
    start_orchestrator,
)

# ---------------------------------------------------------------------------
# WorkerSpec / WorkerMetrics
# ---------------------------------------------------------------------------


def test_worker_spec_snapshot_returns_metrics() -> None:
    """WorkerSpec.snapshot() returns a WorkerMetrics with matching fields."""
    spec = WorkerSpec(
        name="test_worker",
        interval_s=10.0,
        seed=42,
        step=3,
        success_count=2,
        error_count=1,
        last_duration_s=0.05,
    )
    m = spec.snapshot()
    assert isinstance(m, WorkerMetrics)
    assert m.name == "test_worker"
    assert m.step == 3
    assert m.success_count == 2
    assert m.error_count == 1
    assert m.last_duration_s == 0.05


def test_worker_metrics_to_dict_keys() -> None:
    """WorkerMetrics.to_dict() returns all expected keys."""
    m = WorkerMetrics(
        name="wk",
        step=1,
        success_count=1,
        error_count=0,
        last_duration_s=0.01,
        last_run_monotonic=0.0,
    )
    d = m.to_dict()
    assert set(d.keys()) == {
        "name",
        "step",
        "success_count",
        "error_count",
        "last_duration_s",
        "last_run_monotonic",
    }


# ---------------------------------------------------------------------------
# OrchestratorError and _execute_safely
# ---------------------------------------------------------------------------


def test_orchestrator_error_wraps_underlying() -> None:
    """OrchestratorError preserves the original exception as __cause__."""
    spec = WorkerSpec(name="probe", interval_s=1.0, seed=0)

    def bad_handler(_s: WorkerSpec) -> None:
        msg = "boom"
        raise ValueError(msg)

    with pytest.raises(OrchestratorError) as exc_info:
        _execute_safely(bad_handler, spec)
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_execute_safely_succeeds_for_good_handler() -> None:
    """_execute_safely does not raise when handler returns normally."""
    spec = WorkerSpec(name="noop", interval_s=1.0, seed=0)

    def noop(_s: WorkerSpec) -> None:
        return

    _execute_safely(noop, spec)  # should not raise


# ---------------------------------------------------------------------------
# AutonomousOrchestrator lifecycle
# ---------------------------------------------------------------------------


def test_initialize_starts_scheduler_thread() -> None:
    """initialize() starts the daemon scheduler thread."""
    orch = AutonomousOrchestrator(seed=1)
    orch.initialize()
    try:
        assert orch._initialized
        assert orch._scheduler_thread is not None
        assert orch._scheduler_thread.is_alive()
    finally:
        orch.terminate()


def test_double_initialize_raises() -> None:
    """Calling initialize() twice raises RuntimeError."""
    orch = AutonomousOrchestrator(seed=2)
    orch.initialize()
    try:
        with pytest.raises(RuntimeError):
            orch.initialize()
    finally:
        orch.terminate()


def test_negative_seed_raises() -> None:
    """initialize() with seed < 0 raises ValueError."""
    orch = AutonomousOrchestrator(seed=-1)
    with pytest.raises(ValueError):
        orch.initialize()


def test_validate_before_initialize_returns_invalid() -> None:
    """validate() returns invalid ValidationResult before initialize()."""
    orch = AutonomousOrchestrator(seed=3)
    result = orch.validate()
    assert not result.valid
    assert "not initialized" in result.message


def test_validate_after_initialize_returns_valid() -> None:
    """validate() returns valid result after initialize()."""
    orch = AutonomousOrchestrator(seed=4)
    orch.initialize()
    try:
        result = orch.validate()
        assert result.valid
        assert "operational" in result.message
    finally:
        orch.terminate()


def test_operate_after_initialize_does_not_raise() -> None:
    """operate() runs without error on initialized orchestrator."""
    orch = AutonomousOrchestrator(seed=5)
    orch.initialize()
    try:
        orch.operate()  # should not raise
    finally:
        orch.terminate()


def test_operate_before_initialize_does_not_raise() -> None:
    """operate() is a no-op (does not raise) before initialization."""
    orch = AutonomousOrchestrator(seed=6)
    orch.operate()  # should not raise


def test_reconcile_after_initialize_does_not_raise() -> None:
    """reconcile() runs without error on initialized orchestrator."""
    orch = AutonomousOrchestrator(seed=7)
    orch.initialize()
    try:
        orch.reconcile()  # should not raise
    finally:
        orch.terminate()


def test_checkpoint_returns_expected_keys() -> None:
    """checkpoint() returns a dict with all expected keys."""
    orch = AutonomousOrchestrator(seed=8)
    orch.initialize()
    try:
        cp = orch.checkpoint()
        assert cp["component"] == "AutonomousOrchestrator"
        assert cp["initialized"] is True
        assert isinstance(cp["worker_count"], int)
        assert isinstance(cp["workers"], list)
        assert isinstance(cp["uptime_s"], float)
    finally:
        orch.terminate()


def test_terminate_stops_scheduler() -> None:
    """terminate() stops the scheduler thread."""
    orch = AutonomousOrchestrator(seed=9)
    orch.initialize()
    thread = orch._scheduler_thread
    orch.terminate()
    assert not orch._initialized
    if thread is not None:
        # Allow up to 6 s for the thread to exit (join timeout is 5 s)
        thread.join(timeout=6.0)
        assert not thread.is_alive()


def test_get_metrics_structure() -> None:
    """get_metrics() returns a dict with the required top-level keys."""
    orch = AutonomousOrchestrator(seed=10)
    orch.initialize()
    try:
        metrics = orch.get_metrics()
        assert "initialized" in metrics
        assert "uptime_s" in metrics
        assert "worker_count" in metrics
        assert "queue_size" in metrics
        assert "workers" in metrics
        assert "system" in metrics
    finally:
        orch.terminate()


def test_get_metrics_worker_names() -> None:
    """get_metrics() includes all registered worker names."""
    orch = AutonomousOrchestrator(seed=11)
    orch.initialize()
    try:
        metrics = orch.get_metrics()
        worker_names = set(metrics["workers"].keys())
        expected = {
            "coherence_amplification",
            "knowledge_graph_enrichment",
            "constraint_solving",
            "cache_warming",
            "session_maintenance",
            "evidence_gathering",
            "performance_metrics",
        }
        assert expected == worker_names
    finally:
        orch.terminate()


def test_specs_registered_on_initialize() -> None:
    """All 7 worker specs are registered after initialize()."""
    orch = AutonomousOrchestrator(seed=12)
    orch.initialize()
    try:
        assert len(orch._specs) == 7
    finally:
        orch.terminate()


def test_workers_are_daemon_thread() -> None:
    """The scheduler thread is a daemon thread."""
    orch = AutonomousOrchestrator(seed=13)
    orch.initialize()
    try:
        thread = orch._scheduler_thread
        assert thread is not None
        assert thread.daemon
    finally:
        orch.terminate()


# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------


def test_start_orchestrator_returns_initialized_instance() -> None:
    """start_orchestrator() returns an initialized AutonomousOrchestrator."""
    # Use a fresh orchestrator by resetting module state between tests via
    # direct attribute manipulation (acceptable in test isolation context).
    import thalos_prime.autonomous.orchestrator as orch_mod

    original = orch_mod._orchestrator_instance
    orch_mod._orchestrator_instance = None
    instance: AutonomousOrchestrator | None = None
    try:
        instance = start_orchestrator(seed=99)
        assert instance._initialized
        # Second call returns the same instance
        same = start_orchestrator(seed=0)
        assert same is instance
    finally:
        if instance is not None and instance._initialized:
            instance.terminate()
        orch_mod._orchestrator_instance = original


def test_get_orchestrator_returns_none_before_start() -> None:
    """get_orchestrator() returns None when no instance has been started."""
    import thalos_prime.autonomous.orchestrator as orch_mod

    original = orch_mod._orchestrator_instance
    orch_mod._orchestrator_instance = None
    try:
        result = get_orchestrator()
        assert result is None
    finally:
        orch_mod._orchestrator_instance = original


def test_lifecycle_events_recorded() -> None:
    """initialize/validate/operate/reconcile/checkpoint/terminate emit events."""
    orch = AutonomousOrchestrator(seed=14)
    orch.initialize()
    try:
        orch.validate()
        orch.operate()
        orch.reconcile()
        orch.checkpoint()
    finally:
        orch.terminate()
    events = orch.get_events()
    method_names = [e.method for e in events]
    for expected in ("initialize", "validate", "operate", "reconcile", "checkpoint", "terminate"):
        assert expected in method_names, f"Expected lifecycle event {expected!r} not found"


def test_multiple_orchestrators_independent() -> None:
    """Two independently created orchestrators do not share state."""
    orch_a = AutonomousOrchestrator(seed=20)
    orch_b = AutonomousOrchestrator(seed=21)
    orch_a.initialize()
    orch_b.initialize()
    try:
        assert orch_a._scheduler_thread is not orch_b._scheduler_thread
    finally:
        orch_a.terminate()
        orch_b.terminate()


def test_operate_restarts_dead_scheduler() -> None:
    """operate() restarts the scheduler thread if it has unexpectedly died."""
    orch = AutonomousOrchestrator(seed=30)
    orch.initialize()
    try:
        # Force the scheduler to stop without going through terminate()
        orch._stop_event.set()
        old_thread = orch._scheduler_thread
        assert old_thread is not None
        old_thread.join(timeout=3.0)
        assert not old_thread.is_alive()
        # operate() should restart the scheduler
        orch._stop_event.clear()
        orch.operate()
        time.sleep(0.1)
        new_thread = orch._scheduler_thread
        assert new_thread is not None
        assert new_thread.is_alive()
    finally:
        orch.terminate()


def test_checkpoint_after_terminate_returns_not_initialized() -> None:
    """checkpoint() after terminate() shows initialized=False."""
    orch = AutonomousOrchestrator(seed=31)
    orch.initialize()
    orch.terminate()
    cp = orch.checkpoint()
    assert cp["initialized"] is False


def test_thread_safety_get_metrics() -> None:
    """get_metrics() is thread-safe under concurrent reads."""
    orch = AutonomousOrchestrator(seed=40)
    orch.initialize()
    results: list[dict[str, object]] = []
    errors: list[Exception] = []

    def read_metrics() -> None:
        try:
            results.extend([orch.get_metrics() for _ in range(20)])
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=read_metrics) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    orch.terminate()
    assert not errors, f"Thread-safety errors: {errors}"
    assert len(results) == 100


# ---------------------------------------------------------------------------
# Worker handler unit tests (direct calls to exercise uncovered branches)
# ---------------------------------------------------------------------------


def test_run_performance_metrics_populates_extra() -> None:
    """_run_performance_metrics() stores cpu_percent and mem_rss_mib in extra."""
    spec = WorkerSpec(name="performance_metrics", interval_s=30.0, seed=0)
    _run_performance_metrics(spec)
    assert "cpu_percent" in spec.extra
    assert "mem_rss_mib" in spec.extra
    assert isinstance(spec.extra["cpu_percent"], float)
    assert isinstance(spec.extra["mem_rss_mib"], float)
    assert spec.extra["mem_rss_mib"] > 0.0


def test_run_constraint_solving_logs_engine_available() -> None:
    """_run_constraint_solving() completes without error and logs engine availability."""
    spec = WorkerSpec(name="constraint_solving", interval_s=180.0, seed=0)
    _run_constraint_solving(spec)  # should not raise


def test_run_session_maintenance_prunes_empty_sessions() -> None:
    """_run_session_maintenance() removes sessions with no history and sequence=0."""
    from thalos_runtime.plugins.chat_task import SESSION_STORE

    # Inject test sessions
    SESSION_STORE.sessions["_test_abandoned_1"] = {"history": [], "sequence": 0}
    SESSION_STORE.sessions["_test_active_2"] = {
        "history": [{"role": "user", "content": "hi"}],
        "sequence": 1,
    }
    before_count = len(SESSION_STORE.sessions)
    spec = WorkerSpec(name="session_maintenance", interval_s=600.0, seed=0)
    _run_session_maintenance(spec)
    after_count = len(SESSION_STORE.sessions)
    # The abandoned session should be pruned
    assert "_test_abandoned_1" not in SESSION_STORE.sessions
    # The active session should be retained
    assert "_test_active_2" in SESSION_STORE.sessions
    assert after_count <= before_count
    # Clean up
    SESSION_STORE.sessions.pop("_test_active_2", None)


def test_validate_returns_invalid_when_scheduler_not_alive() -> None:
    """validate() returns invalid when scheduler thread is stopped."""
    orch = AutonomousOrchestrator(seed=50)
    orch.initialize()
    # Stop scheduler thread directly
    orch._stop_event.set()
    thread = orch._scheduler_thread
    if thread is not None:
        thread.join(timeout=3.0)
    # validate() should detect the dead thread
    result = orch.validate()
    assert not result.valid
    assert "not alive" in result.message
    # Cleanup without going through normal terminate
    orch._initialized = False


def test_reconcile_warns_when_queue_near_full() -> None:
    """reconcile() logs a warning when task queue utilisation exceeds threshold."""
    from thalos_prime.autonomous.orchestrator import _WORKER_QUEUE_MAX

    orch = AutonomousOrchestrator(seed=51)
    orch.initialize()
    try:
        # Fill queue to 85% capacity
        fill_count = int(_WORKER_QUEUE_MAX * 0.85)
        for i in range(fill_count):
            spec = WorkerSpec(name=f"filler_{i}", interval_s=1.0, seed=i)
            try:
                orch._task_queue.put_nowait(spec)
            except Exception:  # noqa: BLE001
                break
        # reconcile() should warn (no assertion on log content, just no error)
        orch.reconcile()  # should not raise
    finally:
        orch.terminate()


def test_run_coherence_amplification_evicts_low_quality() -> None:
    """_run_coherence_amplification() evicts low-coherence entries from SEARCH_CACHE."""
    from thalos_prime.api.routes.search import SEARCH_CACHE
    from thalos_prime.autonomous.orchestrator import _run_coherence_amplification

    # Insert a guaranteed low-coherence entry (blank page → score near 0)
    test_key = "_test_orch_low_quality_evict_XYZ"
    test_key_empty = "_test_orch_empty_page_XYZ"
    SEARCH_CACHE[test_key] = ({"page": "a b", "query": "xyz"}, 0.0)
    # Also insert an entry with empty page to exercise the `continue` branch
    SEARCH_CACHE[test_key_empty] = ({"page": "", "query": "xyz"}, 0.0)
    before_present = test_key in SEARCH_CACHE

    spec = WorkerSpec(name="coherence_amplification", interval_s=60.0, seed=0)
    _run_coherence_amplification(spec)

    # The low-quality entry should have been evicted
    assert before_present, "Test setup failed: key not inserted"
    assert test_key not in SEARCH_CACHE, "Low-quality entry should have been evicted"
    # Clean up empty page entry (not evicted since page is empty — skipped)
    SEARCH_CACHE.pop(test_key_empty, None)


def test_scheduler_loop_dispatches_workers() -> None:
    """Scheduler loop dispatches registered workers when interval elapses."""
    # Create an orchestrator and force all specs to have last_run_s=0 so
    # every worker is immediately eligible on the first scheduler tick.
    orch = AutonomousOrchestrator(seed=60)
    orch.initialize()
    try:
        # Reset all intervals to 0 so workers run immediately
        for spec in orch._specs:
            spec.interval_s = 0.0
            spec.last_run_s = 0.0
        # Wait for the scheduler to make at least one pass
        time.sleep(0.5)
        # At least the performance_metrics worker should have stepped
        perf_spec = next(
            (s for s in orch._specs if s.name == "performance_metrics"), None
        )
        assert perf_spec is not None
        assert perf_spec.step >= 1
    finally:
        orch.terminate()


def test_scheduler_loop_handles_worker_error() -> None:
    """Scheduler loop increments error_count when a worker raises OrchestratorError."""
    import unittest.mock

    from thalos_prime.autonomous.orchestrator import _HANDLER_REGISTRY

    def _failing_handler(_s: WorkerSpec) -> None:
        msg = "injected test failure"
        raise RuntimeError(msg)

    with unittest.mock.patch.dict(
        _HANDLER_REGISTRY,
        {"performance_metrics": _failing_handler},
    ):
        orch = AutonomousOrchestrator(seed=61)
        orch.initialize()
        try:
            # Force immediate run by setting last_run_s to 0 so the scheduler
            # picks up the worker on its next poll (within _SCHEDULER_POLL_S = 1 s)
            perf_spec = next(s for s in orch._specs if s.name == "performance_metrics")
            perf_spec.interval_s = 0.0
            perf_spec.last_run_s = 0.0
            # Wait for at least two scheduler ticks (> _SCHEDULER_POLL_S)
            time.sleep(1.5)
            assert perf_spec.error_count >= 1
        finally:
            orch.terminate()


def test_scheduler_skips_unknown_handler() -> None:
    """Scheduler loop skips specs with no registered handler (handler is None)."""
    orch = AutonomousOrchestrator(seed=70)
    orch.initialize()
    try:
        # Add a spec for a handler that isn't in the registry
        unknown_spec = WorkerSpec(
            name="__no_such_handler__",
            interval_s=0.0,
            seed=99,
        )
        orch._specs.append(unknown_spec)
        unknown_spec.last_run_s = 0.0
        # Wait for the scheduler to process the spec
        time.sleep(1.5)
        # The spec should have been reached (step incremented) but not dispatched
        assert unknown_spec.step >= 1
        assert unknown_spec.success_count == 0
        assert unknown_spec.error_count == 0
    finally:
        orch.terminate()


def test_run_knowledge_graph_enrichment_with_matching_nodes() -> None:
    """_run_knowledge_graph_enrichment() adds edges between same-prefix nodes."""
    import unittest.mock

    from thalos_prime.autonomous.orchestrator import _run_knowledge_graph_enrichment
    from thalos_prime.graph_rag.interfaces import GraphNode
    from thalos_prime.graph_rag.simple_graph import SimpleKnowledgeGraph

    # Build a graph with two nodes sharing the same 4-char prefix
    g = SimpleKnowledgeGraph(seed=0)
    g.initialize()
    g.add_node(GraphNode(node_id="n1", label="testAlpha"))
    g.add_node(GraphNode(node_id="n2", label="testBeta"))

    spec = WorkerSpec(name="knowledge_graph_enrichment", interval_s=120.0, seed=0)
    # Patch at the definition site; prevent re-initialization (which clears nodes)
    with (
        unittest.mock.patch(
            "thalos_prime.graph_rag.simple_graph.SimpleKnowledgeGraph",
            return_value=g,
        ),
        unittest.mock.patch.object(g, "initialize"),
    ):
        _run_knowledge_graph_enrichment(spec)
    # Edge should have been added between n1 and n2 (both start with "test")
    assert g.edge_count() >= 1


def test_run_evidence_gathering_with_nodes() -> None:
    """_run_evidence_gathering() ingests node labels when the graph has nodes."""
    import unittest.mock

    from thalos_prime.autonomous.orchestrator import _run_evidence_gathering
    from thalos_prime.graph_rag.interfaces import GraphNode
    from thalos_prime.graph_rag.simple_graph import SimpleKnowledgeGraph

    g = SimpleKnowledgeGraph(seed=0)
    g.initialize()
    g.add_node(GraphNode(node_id="ev1", label="epistemic node one"))
    g.add_node(GraphNode(node_id="ev2", label="epistemic node two"))

    spec = WorkerSpec(name="evidence_gathering", interval_s=240.0, seed=0)
    # Patch at the definition site; prevent re-initialization (which clears nodes)
    with (
        unittest.mock.patch(
            "thalos_prime.graph_rag.simple_graph.SimpleKnowledgeGraph",
            return_value=g,
        ),
        unittest.mock.patch.object(g, "initialize"),
    ):
        _run_evidence_gathering(spec)  # should not raise
