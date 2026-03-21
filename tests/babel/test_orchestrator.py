"""Orchestrator lifecycle tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from thalos_prime.babel.control.orchestrator import SystemPhase
from thalos_prime.babel.control.semantic_orchestrator import SemanticOrchestrator

if TYPE_CHECKING:
    from pathlib import Path


def test_status_after_initialize(temp_storage: Path) -> None:
    orch = SemanticOrchestrator(temp_storage)
    orch.initialize()
    status = orch.get_status()
    assert status.phase == SystemPhase.OPERATIONAL
    assert status.integrity_verified is True


def test_checkpoint_creation(temp_storage: Path) -> None:
    orch = SemanticOrchestrator(temp_storage)
    orch.initialize()
    path = orch.checkpoint()
    assert path.exists()
    assert path.read_text(encoding="utf-8")
