"""Tests for knowledge_engine.workers.autonomy_loop."""

from __future__ import annotations

import pytest

from thalos_prime.knowledge_engine.workers.autonomy_loop import AutonomyWorker


def test_autonomy_worker_lifecycle() -> None:
    worker = AutonomyWorker(interval_seconds=60)
    worker.initialize()
    worker.validate()
    worker.operate()
    worker.reconcile()
    cp = worker.checkpoint()
    assert cp["component"] == "AutonomyWorker"
    assert cp["interval_seconds"] == 60
    worker.terminate()


def test_autonomy_worker_invalid_interval() -> None:
    worker = AutonomyWorker(interval_seconds=0)
    with pytest.raises(ValueError, match="interval_seconds must be > 0"):
        worker.initialize()


def test_autonomy_worker_negative_interval() -> None:
    worker = AutonomyWorker(interval_seconds=-5)
    with pytest.raises(ValueError, match="interval_seconds must be > 0"):
        worker.initialize()


def test_autonomy_worker_validate_not_initialized() -> None:
    worker = AutonomyWorker()
    with pytest.raises(RuntimeError, match="not initialized"):
        worker.validate()


def test_autonomy_worker_operate_not_initialized() -> None:
    worker = AutonomyWorker()
    with pytest.raises(RuntimeError, match="not initialized"):
        worker.operate()


def test_autonomy_worker_reconcile_not_initialized() -> None:
    worker = AutonomyWorker()
    with pytest.raises(RuntimeError, match="not initialized"):
        worker.reconcile()


def test_detect_gaps() -> None:
    worker = AutonomyWorker()
    worker.initialize()
    worker.detect_gaps()
    cp = worker.checkpoint()
    assert cp["job_count"] == 1
    worker.terminate()


def test_revalidate_claims() -> None:
    worker = AutonomyWorker()
    worker.initialize()
    worker.revalidate_claims()
    cp = worker.checkpoint()
    assert cp["job_count"] == 1
    worker.terminate()


def test_promote_demote_claims() -> None:
    worker = AutonomyWorker()
    worker.initialize()
    worker.promote_demote_claims()
    worker.promote_demote_claims()
    cp = worker.checkpoint()
    assert cp["job_count"] == 2
    worker.terminate()


def test_refresh_stale_knowledge() -> None:
    worker = AutonomyWorker()
    worker.initialize()
    worker.refresh_stale_knowledge()
    cp = worker.checkpoint()
    assert cp["job_count"] == 1
    worker.terminate()


def test_checkpoint_running_false_initially() -> None:
    worker = AutonomyWorker()
    worker.initialize()
    cp = worker.checkpoint()
    assert cp["running"] is False
    worker.terminate()
