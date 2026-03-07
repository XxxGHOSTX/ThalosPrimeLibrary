"""Base orchestrator for Babel subsystem."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from thalos_prime.babel.core.validation import SystemValidator

from .checkpoint import CheckpointManager
from .reconciler import Reconciler
from .state_manager import FileStateManager

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)


class SystemPhase(Enum):
    """System-level lifecycle phases for the orchestrator."""

    INITIALIZING = auto()
    VALIDATING = auto()
    OPERATIONAL = auto()
    HALTED = auto()


@dataclass(frozen=True)
class SystemStatus:
    """Immutable snapshot of current orchestrator status."""

    phase: SystemPhase
    conversations_handled: int
    last_coordinate: str | None
    integrity_verified: bool


class ThalobalOrchestrator:
    """Control-plane orchestrator handling lifecycle and state."""

    def __init__(self, storage_path: Path, seed: str = "thalos-babel-seed") -> None:
        """Initialize orchestrator with storage path, seed, and all subsystems."""
        self.storage_path = storage_path
        self.seed = seed
        self.phase = SystemPhase.INITIALIZING
        self.state_manager = FileStateManager(self.storage_path)
        self.checkpoint_manager = CheckpointManager(self.storage_path)
        self.reconciler = Reconciler()
        self.validator = SystemValidator()
        self.state = self.state_manager.load()
        self._ensure_storage_layout()

    def initialize(self) -> None:
        """Transition to VALIDATING phase, run validators, then enter OPERATIONAL."""
        self.phase = SystemPhase.VALIDATING
        self.validate()
        self.phase = SystemPhase.OPERATIONAL

    def validate(self) -> None:
        """Run all registered validators; raise RuntimeError on any failure."""
        results = self.validator.validate_all()
        failures = [r for r in results if not r.passed]
        if failures:
            msg = f"Validation failed: {[f.message for f in failures]}"
            raise RuntimeError(msg)

    def get_status(self) -> SystemStatus:
        """Return an immutable snapshot of current orchestrator status."""
        return SystemStatus(
            phase=self.phase,
            conversations_handled=self.state.conversations_handled,
            last_coordinate=self.state.last_coordinate,
            integrity_verified=self.state.integrity_verified,
        )

    def checkpoint(self) -> Path:
        """Serialize current state to a checkpoint file and return its path."""
        return self.checkpoint_manager.create(self.state)

    def reconcile(self) -> None:
        """Detect and resolve state inconsistencies; raise on critical issues."""
        inconsistencies = self.reconciler.check_state(self.state.last_coordinate)
        self.reconciler.resolve(inconsistencies)

    def terminate(self) -> None:
        """Transition orchestrator to HALTED phase."""
        self.phase = SystemPhase.HALTED

    def operate(self) -> None:
        """Execute one operational cycle, logging phase and conversation count."""
        _log.info(
            "operate: phase=%s conversations=%d",
            self.phase,
            self.state.conversations_handled,
        )

    def _record_state(self, coordinate: str) -> None:
        self.state = self.state_manager.record_conversation(self.state, coordinate)

    def _ensure_storage_layout(self) -> None:
        for sub in ("conversations", "coordinates", "audit"):
            target = self.storage_path / sub
            target.mkdir(parents=True, exist_ok=True)
