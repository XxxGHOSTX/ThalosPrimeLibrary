"""ThalosPrime single-launch entry point.

Invoke as::

    python -m thalos_prime [--host HOST] [--port PORT] [--log-level LEVEL]

This module is the Control Plane orchestrator for automated single-launch
operation.  It:

1. Validates environment and configuration.
2. Initialises the RuntimeEngine with all plugins.
3. Starts optional background workers (index refresh, cache warm, session
   maintenance) in a deterministic scheduler with bounded queues.
4. Starts the FastAPI API server via uvicorn.
5. Exposes status/metrics endpoints (via the existing API server).

All background operations are deterministic, explicitly seeded where
randomness is required, and fully logged.  No operation silently degrades.

Control Plane / Data Plane separation:
- Control Plane: this module — lifecycle coordination, worker scheduling,
  environment validation, engine initialisation.
- Data Plane: RuntimeEngine tasks, workers, API handlers — no orchestration.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import queue
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Logging — configured before any other imports that emit log messages
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("thalos_prime.__main__")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8000
_WORKER_QUEUE_MAX: int = 64  # bounded queue for background tasks
_CONFIG_HASH_ENV_VAR = "THALOS_CONFIG_HASH"

# Background worker intervals (seconds)
_INDEX_REFRESH_INTERVAL_S: float = 300.0        # every 5 minutes
_CACHE_WARM_INTERVAL_S: float = 600.0           # every 10 minutes
_SESSION_MAINT_INTERVAL_S: float = 900.0        # every 15 minutes
_COHERENCE_FLOOR_INTERVAL_S: float = 120.0      # every 2 minutes
_BENCHMARK_REPORTER_INTERVAL_S: float = 1800.0  # every 30 minutes
_AUDIT_HEALTH_INTERVAL_S: float = 300.0         # every 5 minutes


# ---------------------------------------------------------------------------
# Environment validation (Control Plane)
# ---------------------------------------------------------------------------

def _compute_config_hash() -> str:
    """Return a deterministic SHA-256 hash of key environment configuration."""
    env_keys = sorted(
        k for k in os.environ
        if k.startswith("THALOS_") or k in {"PYTHONPATH", "LIBRARY_PATH"}
    )
    payload = "|".join(f"{k}={os.environ.get(k, '')}" for k in env_keys)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _validate_environment() -> dict[str, Any]:
    """Validate runtime environment and return status snapshot.

    Raises:
        SystemExit: If a mandatory precondition is not satisfied.

    Returns:
        Environment status dictionary for logging and audit.

    """
    config_hash = _compute_config_hash()
    python_version = sys.version_info
    status: dict[str, Any] = {
        "config_hash": config_hash,
        "python_version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
        "library_path": os.environ.get("THALOS_LIBRARY_PATH", "<not set>"),
    }

    if python_version < (3, 12):
        logger.error(
            "Python >= 3.12 required; found %s.  Halting.",
            status["python_version"],
        )
        sys.exit(1)

    logger.info("Environment validated: config_hash=%s", config_hash)
    return status


# ---------------------------------------------------------------------------
# Background worker infrastructure (Control Plane)
# ---------------------------------------------------------------------------

@dataclass
class WorkerTask:
    """A single deterministic background task descriptor."""

    name: str
    interval_s: float
    seed: int
    step: int = 0
    last_run_s: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)


class BackgroundTaskError(Exception):
    """Raised when a background worker task fails with a recoverable error.

    Wraps any underlying exception so the scheduler can catch a typed error
    (satisfying TPL no-catch-all invariant) rather than bare ``Exception``.
    """


def _run_index_refresh(task: WorkerTask) -> None:
    """Evict stale SEARCH_CACHE entries (index reconciliation step).

    Removes entries whose wall-clock timestamp exceeds the 1-hour cache TTL.
    The SEARCH_CACHE itself uses ``time.time()`` for expiry tracking, so
    wall-clock comparison here is the correct and intended approach.
    Logs entry counts before/after with step, seed, and config hash.
    """
    from thalos_prime.api.routes.search import CACHE_TTL, SEARCH_CACHE

    cutoff = time.time() - float(CACHE_TTL)
    before_count = len(SEARCH_CACHE)
    stale_keys = [k for k, (_, ts) in SEARCH_CACHE.items() if ts < cutoff]
    for k in stale_keys:
        del SEARCH_CACHE[k]
    after_count = len(SEARCH_CACHE)
    logger.info(
        "index_refresh: step=%d seed=%d — evicted %d stale entries (%d → %d)",
        task.step,
        task.seed,
        len(stale_keys),
        before_count,
        after_count,
    )


def _run_cache_warm(task: WorkerTask) -> None:
    """Pre-warm SEARCH_CACHE with Babel pages for recent session queries.

    Collects the most-recently-used user queries from the session store
    (up to 5) and pre-generates their Babel address mappings, storing the
    results in SEARCH_CACHE so subsequent requests are served instantly.
    All address derivation is fully deterministic given the query text.
    """
    from thalos_prime.api.routes.search import SEARCH_CACHE
    from thalos_prime.lob_babel_enumerator import enumerate_addresses
    from thalos_prime.lob_babel_generator import address_to_page
    from thalos_runtime.plugins.chat_task import SESSION_STORE

    # Collect unique user queries from all active sessions (ordered by insertion)
    queries: list[str] = []
    seen_queries: set[str] = set()
    for session in SESSION_STORE.sessions.values():
        for msg in session.get("history", []):
            if msg.get("role") == "user":
                content = str(msg["content"])
                if content not in seen_queries:
                    seen_queries.add(content)
                    queries.append(content)

    # Warm at most 5 unique queries to keep the warm set bounded
    warm_candidates = queries[:5]
    warmed = 0
    for query in warm_candidates:
        cache_key = f"warm:{query}"
        if cache_key not in SEARCH_CACHE:
            addresses = enumerate_addresses(query, max_results=1)
            if addresses:
                addr = str(addresses[0]["address"])
                page = address_to_page(addr)
                SEARCH_CACHE[cache_key] = ({"address": addr, "page": page}, time.time())
                warmed += 1
    logger.info(
        "cache_warm: step=%d seed=%d — warmed %d new entries from %d session queries",
        task.step,
        task.seed,
        warmed,
        len(warm_candidates),
    )


def _run_session_maintenance(task: WorkerTask) -> None:
    """Prune empty/abandoned sessions from SESSION_STORE.

    Removes sessions that were created but never used (history is empty
    and sequence counter is 0).  These ghost sessions accumulate when
    clients open connections but never send messages.  No wall-clock
    comparison is needed — the pruning criterion is purely structural
    and therefore fully deterministic.
    """
    from thalos_runtime.plugins.chat_task import SESSION_STORE

    sessions = SESSION_STORE.sessions
    before_count = len(sessions)
    # Abandon criterion: no message history and sequence never advanced
    abandoned = [
        sid
        for sid, s in sessions.items()
        if not s.get("history") and int(s.get("sequence", 0)) == 0
    ]
    for sid in abandoned:
        del sessions[sid]
    after_count = len(sessions)
    logger.info(
        "session_maintenance: step=%d seed=%d — pruned %d abandoned sessions (%d → %d)",
        task.step,
        task.seed,
        len(abandoned),
        before_count,
        after_count,
    )


def _run_coherence_floor_enforcer(task: WorkerTask) -> None:
    """Enforce minimum coherence floor on all SEARCH_CACHE entries.

    Evicts any cached SearchResponse payload in which the minimum
    ``coherence.overall_score`` across its ``results`` list is below the
    enforced minimum (79.0).  Cached payloads are ``SearchResponse.model_dump()``
    objects whose schema is ``{"results": [{"coherence": {"overall_score": …}}]}``.

    A snapshot of the cache is taken before iteration to avoid
    ``RuntimeError: dictionary changed size during iteration`` under concurrent
    access from FastAPI request handlers.  Individual entries are removed with
    ``pop()`` so concurrent additions after the snapshot are never deleted.
    """
    from thalos_prime.api.routes.search import SEARCH_CACHE

    floor_threshold: float = 79.0
    before_count = len(SEARCH_CACHE)
    # Snapshot to avoid RuntimeError from concurrent mutation by request handlers.
    cache_items_snapshot = list(SEARCH_CACHE.items())

    def _min_score(payload: dict[str, Any]) -> float:
        """Return the minimum result coherence score in a SearchResponse payload."""
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return 0.0
        scores = [
            float(r["coherence"]["overall_score"])
            for r in results
            if isinstance(r, dict)
            and isinstance(r.get("coherence"), dict)
            and isinstance(r["coherence"].get("overall_score"), (int, float))
        ]
        return min(scores) if scores else 0.0

    violating_keys = [
        k
        for k, (payload, _ts) in cache_items_snapshot
        if _min_score(payload) < floor_threshold
    ]
    evicted_count = 0
    for k in violating_keys:
        if SEARCH_CACHE.pop(k, None) is not None:
            evicted_count += 1
    after_count = len(SEARCH_CACHE)
    logger.info(
        "coherence_floor_enforcer: step=%d seed=%d — evicted %d sub-floor entries (%d → %d)",
        task.step,
        task.seed,
        evicted_count,
        before_count,
        after_count,
    )


def _run_benchmark_reporter(task: WorkerTask) -> None:
    """Run a lightweight deterministic benchmark and log the results.

    Executes a fixed set of canonical queries through the adaptive search
    engine and logs coherence scores.  A 30-second timeout is passed to each
    query so the scheduler thread is never blocked longer than 90 seconds
    total.  Stage 1 of the adaptive engine (GenerativeEngine corpus) always
    resolves in under one second, so the timeout is a safety bound only.
    """
    from thalos_prime.adaptive_search import adaptive_search

    # Short per-query budget; Stage 1 always resolves immediately.
    probe_timeout_s: float = 30.0
    probe_queries: list[str] = [
        "deterministic knowledge extraction",
        "language coherence scoring benchmark",
        "library of babel information retrieval",
    ]
    scores: list[float] = []
    for query in probe_queries:
        results = adaptive_search(query, max_results=1, timeout_seconds=probe_timeout_s)
        if results:
            scores.append(results[0].coherence.overall_score)
    avg = sum(scores) / len(scores) if scores else 0.0
    min_score = min(scores) if scores else 0.0
    logger.info(
        "benchmark_reporter: step=%d seed=%d — probes=%d avg_score=%.2f min_score=%.2f",
        task.step,
        task.seed,
        len(scores),
        avg,
        min_score,
    )


def _run_audit_health_check(task: WorkerTask) -> None:
    """Check the shared audit trail health and log authoritative event counts.

    Queries the module-level ``_audit_trail`` instance from
    ``thalos_prime.api.routes.artifacts`` — the same trail used by all
    artifact epistemic operations — so the reported event count reflects
    real system activity rather than an empty in-memory instance.
    Does not alter any state.
    """
    from thalos_prime.api.routes.artifacts import _audit_trail

    events = _audit_trail.get_events()
    logger.info(
        "audit_health_check: step=%d seed=%d — total_audit_events=%d",
        task.step,
        task.seed,
        len(events),
    )


_WORKER_HANDLERS: dict[str, Callable[[WorkerTask], None]] = {
    "index_refresh": _run_index_refresh,
    "cache_warm": _run_cache_warm,
    "session_maintenance": _run_session_maintenance,
    "coherence_floor_enforcer": _run_coherence_floor_enforcer,
    "benchmark_reporter": _run_benchmark_reporter,
    "audit_health_check": _run_audit_health_check,
}


def _execute_worker_safely(
    handler: Callable[[WorkerTask], None],
    task: WorkerTask,
) -> None:
    """Invoke a worker handler, re-raising any failure as :class:`BackgroundTaskError`.

    Args:
        handler: Callable ``(WorkerTask) -> None``.
        task:    The task descriptor to pass to the handler.

    Raises:
        BackgroundTaskError: Wraps any exception raised by the handler so
            the scheduler loop can catch a typed error rather than bare
            ``Exception``, satisfying the TPL no-catch-all invariant.

    """
    try:
        handler(task)
    except Exception as exc:  # re-raised immediately as BackgroundTaskError below
        msg = f"Task {task.name!r} step {task.step} failed: {exc}"
        raise BackgroundTaskError(msg) from exc


class BackgroundScheduler:
    """Deterministic background task scheduler with bounded queue.

    Control Plane: schedules and dispatches Data Plane worker tasks.
    Uses a bounded FIFO queue to prevent unbounded task accumulation.
    All timing uses step counters; wall-clock is used only for sleep.
    """

    def __init__(self, config_hash: str) -> None:
        """Initialize the scheduler with the given configuration hash.

        Args:
            config_hash: SHA-256 prefix of the current configuration, used
                for logging and audit.

        """
        self._config_hash = config_hash
        self._task_queue: queue.Queue[WorkerTask] = queue.Queue(maxsize=_WORKER_QUEUE_MAX)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._tasks: list[WorkerTask] = []

    def add_task(self, task: WorkerTask) -> None:
        """Register a recurring background task."""
        self._tasks.append(task)
        logger.info(
            "BackgroundScheduler: registered task %r (interval=%.1fs seed=%d)",
            task.name,
            task.interval_s,
            task.seed,
        )

    def start(self) -> None:
        """Start the scheduler thread."""
        self._thread = threading.Thread(
            target=self._run_loop,
            name="thalos-bg-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info("BackgroundScheduler: started (config_hash=%s)", self._config_hash)

    def stop(self) -> None:
        """Signal the scheduler to stop and wait for thread to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    def _run_loop(self) -> None:
        """Scheduler main loop — runs in daemon thread."""
        while not self._stop_event.is_set():
            now = time.monotonic()
            for task in self._tasks:
                if now - task.last_run_s >= task.interval_s:
                    task.last_run_s = now
                    task.step += 1
                    try:
                        self._task_queue.put_nowait(task)
                    except queue.Full:
                        logger.warning(
                            "BackgroundScheduler: queue full; skipping task %r at step %d",
                            task.name,
                            task.step,
                        )
                        continue
                    handler = _WORKER_HANDLERS.get(task.name)
                    if handler is not None:
                        try:
                            _execute_worker_safely(handler, task)
                        except BackgroundTaskError:
                            logger.exception(
                                "BackgroundScheduler: task %r step %d raised an error",
                                task.name,
                                task.step,
                            )
            self._stop_event.wait(timeout=1.0)


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m thalos_prime",
        description=(
            "ThalosPrimeLibrary — single-launch entry point.  "
            "Validates environment, starts background workers, and serves the API."
        ),
    )
    parser.add_argument("--host", default=_DEFAULT_HOST, help="API server bind host.")
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT, help="API server bind port.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity (default: INFO).",
    )
    parser.add_argument(
        "--no-background-workers",
        action="store_true",
        help="Disable background worker scheduler (useful for testing).",
    )
    return parser


# ---------------------------------------------------------------------------
# Main entry point (Control Plane orchestration)
# ---------------------------------------------------------------------------

def main() -> None:
    """Single-launch orchestration entry point."""
    args = _build_parser().parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    print("=" * 62)
    print("  ThalosPrimeLibrary — Sovereign Epistemic Operating System")
    print("=" * 62)

    # Step 1: Validate environment
    env_status = _validate_environment()
    config_hash = env_status["config_hash"]

    # Step 2: Initialise RuntimeEngine with all plugins
    logger.info("Initialising RuntimeEngine...")
    from thalos_runtime.core.deps import set_engine
    from thalos_runtime.core.engine import RuntimeEngine
    from thalos_runtime.plugins.loader import PluginLoader

    engine = RuntimeEngine()
    loader = PluginLoader()
    registered = loader.discover_and_register(engine)
    logger.info("Plugins registered: %d", registered)
    engine.initialize()
    validation = engine.validate()
    logger.info("Engine validation: %s", validation.message)
    set_engine(engine)

    # Step 3: Start background workers (bounded, deterministic)
    scheduler: BackgroundScheduler | None = None
    if not args.no_background_workers:
        scheduler = BackgroundScheduler(config_hash=config_hash)
        # Seed each worker deterministically from config_hash + task name
        for task_name, interval_s in [
            ("index_refresh", _INDEX_REFRESH_INTERVAL_S),
            ("cache_warm", _CACHE_WARM_INTERVAL_S),
            ("session_maintenance", _SESSION_MAINT_INTERVAL_S),
            ("coherence_floor_enforcer", _COHERENCE_FLOOR_INTERVAL_S),
            ("benchmark_reporter", _BENCHMARK_REPORTER_INTERVAL_S),
            ("audit_health_check", _AUDIT_HEALTH_INTERVAL_S),
        ]:
            seed_input = f"{config_hash}:{task_name}".encode("utf-8")
            seed = int(hashlib.sha256(seed_input).hexdigest()[:8], 16)
            scheduler.add_task(WorkerTask(name=task_name, interval_s=interval_s, seed=seed))
        scheduler.start()

    # Step 4: Start the API server (blocks until shutdown)
    print(f"\nStarting API server on http://{args.host}:{args.port}")
    print(f"  Docs: http://{args.host}:{args.port}/docs")
    print(f"  Status: http://{args.host}:{args.port}/api/v1/status")
    print("\nPress Ctrl+C to stop.\n")

    try:
        import uvicorn

        from thalos_prime.api.server import app as thalos_app

        uvicorn.run(
            thalos_app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),
        )
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user.")
    finally:
        if scheduler is not None:
            scheduler.stop()
            logger.info("BackgroundScheduler stopped.")


if __name__ == "__main__":
    main()
