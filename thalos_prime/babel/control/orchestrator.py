"""
Base orchestrator for Babel subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from ..core.validation import SystemValidator
from .state_manager import FileStateManager, SystemState
from .checkpoint import CheckpointManager
from .reconciler import Reconciler


class SystemPhase(Enum):
    INITIALIZING = auto()
    VALIDATING = auto()
    OPERATIONAL = auto()
    HALTED = auto()


@dataclass(frozen=True)
class SystemStatus:
    phase: SystemPhase
    conversations_handled: int
    last_coordinate: Optional[str]
    integrity_verified: bool


class ThalobalOrchestrator:
    """Control-plane orchestrator handling lifecycle and state."""

    def __init__(self, storage_path: Path, seed: str = "thalos-babel-seed") -> None:
        self.storage_path = storage_path
        self.seed = seed
        self.phase = SystemPhase.INITIALIZING
        self.state_manager = FileStateManager(self.storage_path)
        self.checkpoint_manager = CheckpointManager(self.storage_path)
        self.reconciler = Reconciler()
        self.validator = SystemValidator()
        self.state: SystemState = self.state_manager.load()
        self._ensure_storage_layout()

    def initialize(self) -> None:
        self.phase = SystemPhase.VALIDATING
        self.validate()
        self.phase = SystemPhase.OPERATIONAL

    def validate(self) -> None:
        results = self.validator.validate_all()
        failures = [r for r in results if not r.passed]
        if failures:
            raise RuntimeError(f"Validation failed: {[f.message for f in failures]}")

    def get_status(self) -> SystemStatus:
        return SystemStatus(
            phase=self.phase,
            conversations_handled=self.state.conversations_handled,
            last_coordinate=self.state.last_coordinate,
            integrity_verified=self.state.integrity_verified,
        )

    def checkpoint(self) -> Path:
        return self.checkpoint_manager.create(self.state)

    def operate(self) -> None:
        """Execute primary orchestration work: reconcile state and log status."""
        self.reconcile()

    def reconcile(self) -> None:
        inconsistencies = self.reconciler.check_state(self.state.last_coordinate)
        self.reconciler.resolve(inconsistencies)

    def terminate(self) -> None:
        self.phase = SystemPhase.HALTED

    def _record_state(self, coordinate: str) -> None:
        self.state = self.state_manager.record_conversation(self.state, coordinate)

    def _ensure_storage_layout(self) -> None:
        for sub in ("conversations", "coordinates", "audit"):
            target = self.storage_path / sub
            target.mkdir(parents=True, exist_ok=True)
