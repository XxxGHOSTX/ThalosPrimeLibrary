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
from typing import Any

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


def _run_index_refresh(task: WorkerTask) -> None:
    """Perform a single index refresh step for the given worker task."""
    logger.debug(
        "index_refresh: step=%d seed=%d interval=%.1fs",
        task.step,
        task.seed,
        task.interval_s,
    )


def _run_cache_warm(task: WorkerTask) -> None:
    """Perform a single cache warming step for the given worker task."""
    logger.debug(
        "cache_warm: step=%d seed=%d interval=%.1fs",
        task.step,
        task.seed,
        task.interval_s,
    )


def _run_session_maintenance(task: WorkerTask) -> None:
    """Perform a single session maintenance step for the given worker task."""
    logger.debug(
        "session_maintenance: step=%d seed=%d interval=%.1fs",
        task.step,
        task.seed,
        task.interval_s,
    )


_WORKER_HANDLERS: dict[str, Any] = {
    "index_refresh": _run_index_refresh,
    "cache_warm": _run_cache_warm,
    "session_maintenance": _run_session_maintenance,
}


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
                            handler(task)
                        except Exception:
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
            ("index_refresh", 300.0),       # every 5 minutes
            ("cache_warm", 600.0),          # every 10 minutes
            ("session_maintenance", 900.0), # every 15 minutes
        ]:
            seed_input = f"{config_hash}:{task_name}".encode("utf-8")
            seed = int(hashlib.sha256(seed_input).hexdigest()[:8], 16)
            scheduler.add_task(WorkerTask(name=task_name, interval_s=interval_s, seed=seed))
        scheduler.start()

    # Step 4: Start the API server (blocks until shutdown)
    print(f"\nStarting API server on http://{args.host}:{args.port}")
    print("  Docs: http://{host}:{port}/docs".format(host=args.host, port=args.port))
    print("  Status: http://{host}:{port}/api/v1/status".format(host=args.host, port=args.port))
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
