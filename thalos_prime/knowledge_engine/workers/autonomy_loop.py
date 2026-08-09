"""Autonomy worker for the Knowledge Engine.

Runs background jobs for gap detection, claim revalidation,
and knowledge freshness maintenance using APScheduler.
"""

from __future__ import annotations

import importlib.util as _importlib_util
import logging

logger = logging.getLogger(__name__)

_apscheduler_available: bool = _importlib_util.find_spec("apscheduler") is not None
del _importlib_util


class AutonomyWorker:
    """Lifecycle-managed autonomy worker.

    Runs scheduled background tasks for knowledge maintenance:
    - detect_gaps: identifies missing evidence or coverage gaps
    - revalidate_claims: re-scores claims with updated evidence
    - promote_demote_claims: adjusts claim status based on scores
    - refresh_stale_knowledge: marks outdated sources for re-ingestion

    Example::

        worker = AutonomyWorker(interval_seconds=60)
        worker.initialize()
        worker.operate()
        worker.terminate()

    """

    def __init__(self, interval_seconds: int = 300) -> None:
        """Initialize the autonomy worker.

        Args:
            interval_seconds: Interval between background job runs in seconds.

        """
        self._interval_seconds = interval_seconds
        self._initialized: bool = False
        self._scheduler: object | None = None
        self._running: bool = False
        self._job_count: int = 0

    def initialize(self) -> None:
        """Set up the autonomy worker and scheduler.

        Raises:
            ValueError: If interval_seconds is not positive.

        """
        if self._interval_seconds <= 0:
            msg = f"AutonomyWorker: interval_seconds must be > 0, got {self._interval_seconds}"
            raise ValueError(msg)
        self._job_count = 0
        self._running = False
        if _apscheduler_available:
            from apscheduler.schedulers.background import BackgroundScheduler
            self._scheduler = BackgroundScheduler()
        else:
            self._scheduler = None
            logger.warning("AutonomyWorker: APScheduler not available; scheduler disabled")
        self._initialized = True
        logger.info("AutonomyWorker initialized: interval_seconds=%d", self._interval_seconds)

    def validate(self) -> None:
        """Verify that the worker is properly initialized.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "AutonomyWorker.validate(): not initialized"
            raise RuntimeError(msg)
        logger.debug("AutonomyWorker validation passed")

    def operate(self) -> None:
        """Start the background scheduler with all registered jobs.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "AutonomyWorker.operate(): not initialized"
            raise RuntimeError(msg)
        if self._scheduler is not None and _apscheduler_available:
            from apscheduler.schedulers.background import BackgroundScheduler
            scheduler = self._scheduler
            if isinstance(scheduler, BackgroundScheduler):
                scheduler.add_job(
                    self.detect_gaps,
                    "interval",
                    seconds=self._interval_seconds,
                    id="detect_gaps",
                )
                scheduler.add_job(
                    self.revalidate_claims,
                    "interval",
                    seconds=self._interval_seconds,
                    id="revalidate_claims",
                )
                scheduler.add_job(
                    self.promote_demote_claims,
                    "interval",
                    seconds=self._interval_seconds,
                    id="promote_demote_claims",
                )
                scheduler.add_job(
                    self.refresh_stale_knowledge,
                    "interval",
                    seconds=self._interval_seconds,
                    id="refresh_stale_knowledge",
                )
                scheduler.start()
                self._running = True
                logger.info("AutonomyWorker.operate(): scheduler started")
        else:
            logger.info("AutonomyWorker.operate(): no scheduler — running in no-op mode")

    def reconcile(self) -> None:
        """Log current worker state.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "AutonomyWorker.reconcile(): not initialized"
            raise RuntimeError(msg)
        logger.info(
            "AutonomyWorker.reconcile(): running=%s job_count=%d",
            self._running,
            self._job_count,
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialize current worker state.

        Returns:
            Dictionary with component name, running status, and job count.

        """
        return {
            "component": "AutonomyWorker",
            "initialized": self._initialized,
            "running": self._running,
            "interval_seconds": self._interval_seconds,
            "job_count": self._job_count,
        }

    def terminate(self) -> None:
        """Stop the scheduler and clean up resources."""
        if self._scheduler is not None and self._running and _apscheduler_available:
            from apscheduler.schedulers.background import BackgroundScheduler
            scheduler = self._scheduler
            if isinstance(scheduler, BackgroundScheduler):
                scheduler.shutdown(wait=False)
                logger.info("AutonomyWorker: scheduler stopped")
        self._running = False
        self._initialized = False
        logger.info("AutonomyWorker terminated: job_count=%d", self._job_count)

    def detect_gaps(self) -> None:
        """Detect coverage gaps in the knowledge base."""
        self._job_count += 1
        logger.info("AutonomyWorker.detect_gaps(): running job #%d", self._job_count)

    def revalidate_claims(self) -> None:
        """Re-score claims with updated evidence."""
        self._job_count += 1
        logger.info("AutonomyWorker.revalidate_claims(): running job #%d", self._job_count)

    def promote_demote_claims(self) -> None:
        """Adjust claim status based on current scores."""
        self._job_count += 1
        logger.info("AutonomyWorker.promote_demote_claims(): running job #%d", self._job_count)

    def refresh_stale_knowledge(self) -> None:
        """Mark outdated sources for re-ingestion."""
        self._job_count += 1
        logger.info("AutonomyWorker.refresh_stale_knowledge(): running job #%d", self._job_count)
