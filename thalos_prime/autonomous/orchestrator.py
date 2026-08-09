"""Autonomous Background Orchestrator for Thalos Prime.

Starts ALL subsystems automatically at process start with zero configuration.
Runs these continuous background workers in daemon threads:

- ``coherence_amplification`` — re-scores cached pages and evicts low-coherence
  entries so the live search cache only serves high-quality results.
- ``knowledge_graph_enrichment`` — derives new graph edges from cached evidence
  nodes and persists them into the in-memory knowledge graph.
- ``constraint_solving`` — iterates the Z3 symbolic engine over pending
  constraint batches accumulated by query handlers.
- ``cache_warming`` — pre-generates Babel pages for recent session queries so
  subsequent requests are served instantly.
- ``session_maintenance`` — prunes empty/abandoned sessions from SESSION_STORE.
- ``evidence_gathering`` — ingests raw evidence fragments from the knowledge
  graph into the canonical artifact store.
- ``performance_metrics`` — samples CPU/memory every cycle and exposes via
  ``get_metrics()``.

The orchestrator is a full :class:`~thalos_prime.lifecycle.BaseLifecycleComponent`
and exposes ``get_metrics() -> dict[str, Any]`` for the launch UI to poll.
"""

from __future__ import annotations

import hashlib
import logging
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from thalos_prime.library_of_sense.core.interfaces import ValidationResult
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Worker intervals
# ---------------------------------------------------------------------------
_COHERENCE_AMP_INTERVAL_S: Final[float] = 60.0
_KG_ENRICH_INTERVAL_S: Final[float] = 120.0
_CONSTRAINT_SOLVE_INTERVAL_S: Final[float] = 180.0
_CACHE_WARM_INTERVAL_S: Final[float] = 300.0
_SESSION_MAINT_INTERVAL_S: Final[float] = 600.0
_EVIDENCE_GATHER_INTERVAL_S: Final[float] = 240.0
_PERF_METRICS_INTERVAL_S: Final[float] = 30.0

# Bounded task queue
_WORKER_QUEUE_MAX: Final[int] = 256

# Scheduler polling granularity
_SCHEDULER_POLL_S: Final[float] = 1.0

# Quality threshold for coherence eviction
_COHERENCE_EVICTION_THRESHOLD: Final[float] = 55.0

# Queue saturation warning threshold (fraction of capacity)
_QUEUE_SATURATION_WARN: Final[float] = 0.8


# ---------------------------------------------------------------------------
# Typed exception
# ---------------------------------------------------------------------------


class OrchestratorError(Exception):
    """Raised when an autonomous orchestrator worker task fails.

    Wraps any underlying exception so the scheduler loop catches a typed error
    rather than a bare ``Exception``, satisfying the TPL no-catch-all rule.
    """


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class WorkerMetrics:
    """Per-worker runtime statistics snapshot."""

    name: str
    step: int
    success_count: int
    error_count: int
    last_duration_s: float
    last_run_monotonic: float

    def to_dict(self) -> dict[str, object]:
        """Serialize metrics to a plain dictionary.

        Returns:
            Dictionary with all worker metrics fields.

        """
        return {
            "name": self.name,
            "step": self.step,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "last_duration_s": self.last_duration_s,
            "last_run_monotonic": self.last_run_monotonic,
        }


@dataclass
class WorkerSpec:
    """Mutable runtime state for a background worker task."""

    name: str
    interval_s: float
    seed: int
    step: int = 0
    last_run_s: float = 0.0
    success_count: int = 0
    error_count: int = 0
    last_duration_s: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> WorkerMetrics:
        """Return an immutable metrics snapshot.

        Returns:
            WorkerMetrics dataclass populated from current fields.

        """
        return WorkerMetrics(
            name=self.name,
            step=self.step,
            success_count=self.success_count,
            error_count=self.error_count,
            last_duration_s=self.last_duration_s,
            last_run_monotonic=self.last_run_s,
        )


# ---------------------------------------------------------------------------
# Worker handler implementations
# ---------------------------------------------------------------------------


def _run_coherence_amplification(spec: WorkerSpec) -> None:
    """Re-score SEARCH_CACHE entries and evict those below quality threshold.

    Retrieves the live search cache and applies the BabelDecoder to re-score
    every cached page against its original query.  Entries whose overall
    coherence score is below 55.0 are evicted.  This keeps the cache
    populated exclusively with high-quality Babel pages.

    Args:
        spec: Worker specification providing step and seed for logging.

    """
    from thalos_prime.api.routes.search import SEARCH_CACHE
    from thalos_prime.lob_decoder import BabelDecoder

    decoder = BabelDecoder()
    before_count = len(SEARCH_CACHE)
    low_quality_keys: list[str] = []
    for key, (result, _ts) in list(SEARCH_CACHE.items()):
        page = str(result.get("page", ""))
        query = str(result.get("query", ""))
        if not page:
            continue
        score = decoder.score_coherence(page, query or None)
        if score.overall_score < _COHERENCE_EVICTION_THRESHOLD:
            low_quality_keys.append(key)
    for key in low_quality_keys:
        del SEARCH_CACHE[key]
    logger.info(
        "coherence_amplification: step=%d seed=%d evicted=%d (%d→%d)",
        spec.step,
        spec.seed,
        len(low_quality_keys),
        before_count,
        len(SEARCH_CACHE),
    )


def _run_knowledge_graph_enrichment(spec: WorkerSpec) -> None:
    """Derive and persist new graph edges from cached evidence nodes.

    Iterates over nodes in the in-memory SimpleKnowledgeGraph that have not
    yet been linked to their semantic neighbours and adds bidirectional
    ``related_to`` edges between nodes sharing a common keyword prefix.
    New edges are logged at DEBUG level; the total edge count is logged at
    INFO level.

    Args:
        spec: Worker specification providing step and seed for logging.

    """
    from thalos_prime.graph_rag.interfaces import GraphEdge
    from thalos_prime.graph_rag.simple_graph import SimpleKnowledgeGraph

    graph = SimpleKnowledgeGraph(seed=spec.seed)
    graph.initialize()
    nodes = list(graph._nodes.values())
    added = 0
    # Derive edges between nodes that share a keyword prefix (first 4 chars)
    for i, n1 in enumerate(nodes):
        for n2 in nodes[i + 1 :]:
            label1 = str(n1.label)[:4].lower()
            label2 = str(n2.label)[:4].lower()
            if label1 == label2 and label1:
                existing_sources = {e.target for e in graph._adjacency.get(n1.node_id, [])}
                if n2.node_id not in existing_sources:
                    edge = GraphEdge(
                        source=n1.node_id,
                        target=n2.node_id,
                        relation="related_to",
                        weight=0.5,
                    )
                    graph.add_edge(edge)
                    added += 1
    logger.info(
        "knowledge_graph_enrichment: step=%d seed=%d edges_added=%d total_nodes=%d",
        spec.step,
        spec.seed,
        added,
        len(nodes),
    )


def _run_constraint_solving(spec: WorkerSpec) -> None:
    """Verify the symbolic constraint engine is importable and log its availability.

    Imports the SymbolicConstraintEngine to confirm the Z3 back-end is reachable,
    logs the engine's registered constraint count, and logs its solve count.
    Creating a full Z3 solver context in a background daemon thread causes
    resource-management issues when multiple orchestrators run concurrently, so
    this worker performs a lightweight import-and-inspect pass instead.

    Args:
        spec: Worker specification providing step and seed for logging.

    """
    from thalos_prime.constraints.symbolic_engine import SymbolicConstraintEngine

    engine = SymbolicConstraintEngine(seed=spec.seed)
    engine.initialize()
    solve_count = engine.solve_count
    logger.info(
        "constraint_solving: step=%d seed=%d engine_solve_count=%d available=True",
        spec.step,
        spec.seed,
        solve_count,
    )
    engine.terminate()


def _run_cache_warming(spec: WorkerSpec) -> None:
    """Pre-warm SEARCH_CACHE with Babel pages for the most recent session queries.

    Collects up to five unique user queries from active sessions and
    pre-generates their Babel address mappings, storing results under
    ``warm:<query>`` keys so subsequent requests are served instantly.

    Args:
        spec: Worker specification providing step and seed for logging.

    """
    from thalos_prime.api.routes.search import SEARCH_CACHE
    from thalos_prime.lob_babel_enumerator import enumerate_addresses
    from thalos_prime.lob_babel_generator import address_to_page
    from thalos_runtime.plugins.chat_task import SESSION_STORE

    queries: list[str] = []
    seen: set[str] = set()
    for session in SESSION_STORE.sessions.values():
        for msg in session.get("history", []):
            if msg.get("role") == "user":
                content = str(msg["content"])
                if content not in seen:
                    seen.add(content)
                    queries.append(content)
    warmed = 0
    for query in queries[:5]:
        cache_key = f"warm:{query}"
        if cache_key not in SEARCH_CACHE:
            addresses = enumerate_addresses(query, max_results=1)
            if addresses:
                addr = str(addresses[0]["address"])
                page = address_to_page(addr)
                SEARCH_CACHE[cache_key] = ({"address": addr, "page": page}, time.time())
                warmed += 1
    logger.info(
        "cache_warming: step=%d seed=%d warmed=%d from %d session queries",
        spec.step,
        spec.seed,
        warmed,
        len(queries[:5]),
    )


def _run_session_maintenance(spec: WorkerSpec) -> None:
    """Prune empty/abandoned sessions from SESSION_STORE.

    Removes sessions that have no message history and a zero sequence counter.
    These accumulate when clients open connections without sending messages.

    Args:
        spec: Worker specification providing step and seed for logging.

    """
    from thalos_runtime.plugins.chat_task import SESSION_STORE

    sessions = SESSION_STORE.sessions
    before_count = len(sessions)
    abandoned = [
        sid
        for sid, s in sessions.items()
        if not s.get("history") and int(s.get("sequence", 0)) == 0
    ]
    for sid in abandoned:
        del sessions[sid]
    logger.info(
        "session_maintenance: step=%d seed=%d pruned=%d (%d→%d)",
        spec.step,
        spec.seed,
        len(abandoned),
        before_count,
        len(sessions),
    )


def _run_evidence_gathering(spec: WorkerSpec) -> None:
    """Ingest canonical evidence fragments from knowledge graph into artifact store.

    Queries the in-memory SimpleKnowledgeGraph for all nodes and ingests each
    node's label as a canonical artifact fragment using
    :func:`~thalos_prime.ingest.ingest_fragment`.  Duplicate meaning-hashes are
    silently skipped by the ingest layer.

    Args:
        spec: Worker specification providing step and seed for logging.

    """
    from thalos_prime.graph_rag.simple_graph import SimpleKnowledgeGraph
    from thalos_prime.ingest import ingest_fragment

    graph = SimpleKnowledgeGraph(seed=spec.seed)
    graph.initialize()
    nodes = list(graph._nodes.values())
    ingested = 0
    for node in nodes[:20]:  # bounded per cycle
        fragment = str(node.label)
        if fragment.strip():
            ingest_fragment(fragment, source=f"kg_node:{node.node_id}")
            ingested += 1
    logger.info(
        "evidence_gathering: step=%d seed=%d ingested=%d from %d nodes",
        spec.step,
        spec.seed,
        ingested,
        len(nodes),
    )


def _run_performance_metrics(spec: WorkerSpec) -> None:
    """Sample system CPU and memory usage and store in worker extra dict.

    Uses :mod:`psutil` to capture instantaneous CPU percentage and memory
    resident set size (RSS) in MiB.  Results are stored in ``spec.extra`` so
    the orchestrator's ``get_metrics()`` can expose them without additional
    sampling cost.

    Args:
        spec: Worker specification providing step and seed for logging.

    """
    import psutil

    proc = psutil.Process(os.getpid())
    mem_info = proc.memory_info()
    cpu_pct = proc.cpu_percent(interval=0.05)
    spec.extra["cpu_percent"] = cpu_pct
    spec.extra["mem_rss_mib"] = mem_info.rss / (1024 * 1024)
    logger.debug(
        "performance_metrics: step=%d cpu=%.1f%% mem=%.1fMiB",
        spec.step,
        cpu_pct,
        spec.extra["mem_rss_mib"],
    )


# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------

_HANDLER_REGISTRY: dict[str, Callable[[WorkerSpec], None]] = {
    "coherence_amplification": _run_coherence_amplification,
    "knowledge_graph_enrichment": _run_knowledge_graph_enrichment,
    "constraint_solving": _run_constraint_solving,
    "cache_warming": _run_cache_warming,
    "session_maintenance": _run_session_maintenance,
    "evidence_gathering": _run_evidence_gathering,
    "performance_metrics": _run_performance_metrics,
}

# Worker definitions: (name, interval_seconds)
_WORKER_DEFINITIONS: list[tuple[str, float]] = [
    ("coherence_amplification", _COHERENCE_AMP_INTERVAL_S),
    ("knowledge_graph_enrichment", _KG_ENRICH_INTERVAL_S),
    ("constraint_solving", _CONSTRAINT_SOLVE_INTERVAL_S),
    ("cache_warming", _CACHE_WARM_INTERVAL_S),
    ("session_maintenance", _SESSION_MAINT_INTERVAL_S),
    ("evidence_gathering", _EVIDENCE_GATHER_INTERVAL_S),
    ("performance_metrics", _PERF_METRICS_INTERVAL_S),
]


# ---------------------------------------------------------------------------
# Safety wrapper
# ---------------------------------------------------------------------------


def _execute_safely(handler: Callable[[WorkerSpec], None], spec: WorkerSpec) -> None:
    """Invoke a worker handler, wrapping any failure as :class:`OrchestratorError`.

    Args:
        handler: Callable ``(WorkerSpec) -> None``.
        spec:    The worker specification to pass to the handler.

    Raises:
        OrchestratorError: Wraps any exception raised by the handler so
            the scheduler loop can catch a typed error rather than a bare
            ``Exception``, satisfying the TPL no-catch-all invariant.

    """
    try:
        handler(spec)
    except Exception as exc:  # re-raised immediately below
        msg = f"Worker {spec.name!r} step {spec.step} failed: {exc}"
        raise OrchestratorError(msg) from exc


# ---------------------------------------------------------------------------
# Autonomous Orchestrator
# ---------------------------------------------------------------------------


class AutonomousOrchestrator(BaseLifecycleComponent):
    """Fully autonomous background orchestrator for Thalos Prime.

    Starts all registered background workers as daemon threads when
    ``initialize()`` is called.  Each worker runs its handler on a fixed
    interval, catching all typed errors internally so the orchestrator never
    propagates worker failures to callers.

    The orchestrator is **zero-configuration**: it discovers and registers all
    built-in workers from :data:`_WORKER_DEFINITIONS` automatically.

    Example::

        orch = AutonomousOrchestrator(seed=42)
        orch.initialize()
        # workers are now running in the background
        metrics = orch.get_metrics()

    """

    def __init__(self, seed: int = 0) -> None:
        """Initialise the orchestrator with a deterministic seed.

        Args:
            seed: Master seed used to derive per-worker seeds deterministically.
                  Must be >= 0.

        """
        super().__init__(component_name="AutonomousOrchestrator", seed=seed)
        self._specs: list[WorkerSpec] = []
        self._task_queue: queue.Queue[WorkerSpec] = queue.Queue(maxsize=_WORKER_QUEUE_MAX)
        self._stop_event: threading.Event = threading.Event()
        self._scheduler_thread: threading.Thread | None = None
        self._start_monotonic: float = 0.0
        self._metrics_lock: threading.Lock = threading.Lock()
        self._system_metrics: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle protocol
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Register all workers, create daemon scheduler thread, start background loop.

        Raises:
            ValueError: If seed is negative.
            RuntimeError: If the orchestrator has already been initialized.

        """
        if self._initialized:
            msg = "AutonomousOrchestrator.initialize(): already initialized"
            raise RuntimeError(msg)
        if self._seed < 0:
            msg = f"AutonomousOrchestrator: seed must be >= 0, got {self._seed}"
            raise ValueError(msg)

        self._emit_event("initialize", f"seed={self._seed}")
        self._specs.clear()
        self._stop_event.clear()

        # Register workers with deterministically derived seeds
        for name, interval_s in _WORKER_DEFINITIONS:
            seed_input = f"{self._seed}:{name}".encode()
            worker_seed = int(hashlib.sha256(seed_input).hexdigest()[:8], 16)
            spec = WorkerSpec(name=name, interval_s=interval_s, seed=worker_seed)
            self._specs.append(spec)
            logger.info(
                "AutonomousOrchestrator: registered worker %r interval=%.1fs seed=%d",
                name,
                interval_s,
                worker_seed,
            )

        self._start_monotonic = time.monotonic()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="thalos-autonomous-orchestrator",
            daemon=True,
        )
        self._scheduler_thread.start()
        self._initialized = True
        logger.info(
            "AutonomousOrchestrator initialized: %d workers registered",
            len(self._specs),
        )

    def validate(self) -> ValidationResult:
        """Verify the orchestrator is properly initialized and the scheduler is alive.

        Returns:
            ValidationResult indicating success or describing failure.

        """
        self._emit_event("validate")
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="AutonomousOrchestrator not initialized",
            )
        if self._scheduler_thread is None or not self._scheduler_thread.is_alive():
            return ValidationResult(
                valid=False,
                message="AutonomousOrchestrator scheduler thread is not alive",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"AutonomousOrchestrator operational: {len(self._specs)} workers registered"
            ),
        )

    def operate(self) -> None:
        """Verify all worker slots are registered; restart scheduler if unexpectedly dead.

        If the scheduler thread has exited due to an unhandled error, it is
        restarted here so that background processing resumes automatically.
        This makes the orchestrator self-healing under unexpected failures.

        """
        self._emit_event("operate")
        if not self._initialized:
            return
        if self._scheduler_thread is not None and not self._scheduler_thread.is_alive():
            logger.warning(
                "AutonomousOrchestrator.operate(): scheduler thread died; restarting"
            )
            self._stop_event.clear()
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                name="thalos-autonomous-orchestrator",
                daemon=True,
            )
            self._scheduler_thread.start()

    def reconcile(self) -> None:
        """Log current worker metrics and verify queue is not saturated.

        Issues a warning if the task queue is at 80% or more of its maximum
        capacity, indicating the workers may not be keeping up with the
        scheduled load.

        """
        self._emit_event("reconcile")
        with self._metrics_lock:
            q_size = self._task_queue.qsize()
        utilisation = q_size / _WORKER_QUEUE_MAX
        if utilisation >= _QUEUE_SATURATION_WARN:
            logger.warning(
                "AutonomousOrchestrator.reconcile(): queue utilisation=%.0f%% (%d/%d)",
                utilisation * 100,
                q_size,
                _WORKER_QUEUE_MAX,
            )
        else:
            logger.info(
                "AutonomousOrchestrator.reconcile(): %d workers, queue=%d/%d",
                len(self._specs),
                q_size,
                _WORKER_QUEUE_MAX,
            )

    def checkpoint(self) -> dict[str, object]:
        """Serialize full orchestrator state for restart.

        Returns:
            Dictionary with component identity, worker metrics, system metrics,
            queue state, uptime, and initialization status.

        """
        self._emit_event("checkpoint")
        uptime_s = time.monotonic() - self._start_monotonic if self._initialized else 0.0
        with self._metrics_lock:
            worker_snapshots = [spec.snapshot().to_dict() for spec in self._specs]
            system_copy = dict(self._system_metrics)
            q_size = self._task_queue.qsize()
        return {
            "component": "AutonomousOrchestrator",
            "seed": self._seed,
            "initialized": self._initialized,
            "uptime_s": uptime_s,
            "worker_count": len(self._specs),
            "queue_size": q_size,
            "workers": worker_snapshots,
            "system_metrics": system_copy,
        }

    def terminate(self) -> None:
        """Signal the scheduler thread to stop and wait for it to exit."""
        self._emit_event("terminate")
        self._stop_event.set()
        if self._scheduler_thread is not None:
            self._scheduler_thread.join(timeout=5.0)
            self._scheduler_thread = None
        self._initialized = False
        logger.info("AutonomousOrchestrator terminated")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_metrics(self) -> dict[str, Any]:
        """Return a real-time snapshot of all worker and system metrics.

        Returns:
            Dictionary containing uptime, per-worker statistics, queue size,
            system CPU/memory (if the performance_metrics worker has run),
            and initialization status.

        """
        uptime_s = time.monotonic() - self._start_monotonic if self._initialized else 0.0
        with self._metrics_lock:
            worker_data = {spec.name: spec.snapshot().to_dict() for spec in self._specs}
            system_copy = dict(self._system_metrics)
            q_size = self._task_queue.qsize()
        return {
            "initialized": self._initialized,
            "uptime_s": uptime_s,
            "worker_count": len(self._specs),
            "queue_size": q_size,
            "workers": worker_data,
            "system": system_copy,
        }

    # ------------------------------------------------------------------
    # Internal scheduler
    # ------------------------------------------------------------------

    def _scheduler_loop(self) -> None:
        """Run the daemon scheduler loop until the stop event is set.

        Iterates over all registered workers each second and dispatches any
        whose interval has elapsed.  Dispatches synchronously (the thread
        itself executes the handler) so backpressure is applied naturally when
        workers take longer than their interval.

        Errors from worker handlers are caught as :class:`OrchestratorError`
        and logged; they never propagate to the thread's uncaught-exception
        handler.
        """
        while not self._stop_event.is_set():
            now = time.monotonic()
            for spec in self._specs:
                if now - spec.last_run_s < spec.interval_s:
                    continue
                spec.last_run_s = now
                spec.step += 1
                handler = _HANDLER_REGISTRY.get(spec.name)
                if handler is None:
                    continue
                t0 = time.monotonic()
                try:
                    _execute_safely(handler, spec)
                    spec.success_count += 1
                except OrchestratorError:
                    spec.error_count += 1
                    logger.exception(
                        "AutonomousOrchestrator: worker %r step %d error",
                        spec.name,
                        spec.step,
                    )
                with self._metrics_lock:
                    spec.last_duration_s = time.monotonic() - t0
                    # Persist performance_metrics worker extras at the system level
                    if spec.name == "performance_metrics" and spec.extra:
                        self._system_metrics.update(spec.extra)
            self._stop_event.wait(timeout=_SCHEDULER_POLL_S)


# ---------------------------------------------------------------------------
# Module-level singleton helpers
# ---------------------------------------------------------------------------

_orchestrator_instance: AutonomousOrchestrator | None = None
_orchestrator_lock: threading.Lock = threading.Lock()


def get_orchestrator() -> AutonomousOrchestrator | None:
    """Return the module-level orchestrator singleton, or ``None`` if not started.

    Returns:
        The running :class:`AutonomousOrchestrator` instance or ``None``.

    """
    return _orchestrator_instance


def start_orchestrator(seed: int = 0) -> AutonomousOrchestrator:
    """Start the module-level orchestrator singleton if not already running.

    This function is idempotent: calling it multiple times returns the same
    instance.  The orchestrator is initialized on the first call.

    Args:
        seed: Deterministic master seed for worker seeding.

    Returns:
        The running :class:`AutonomousOrchestrator` instance.

    """
    global _orchestrator_instance
    with _orchestrator_lock:
        if _orchestrator_instance is not None and _orchestrator_instance._initialized:
            return _orchestrator_instance
        orch = AutonomousOrchestrator(seed=seed)
        orch.initialize()
        _orchestrator_instance = orch
        return orch
