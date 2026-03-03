"""Base orchestrator for Babel subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from thalos_prime.babel.core.validation import SystemValidator

from .checkpoint import CheckpointManager
from .reconciler import Reconciler
from .state_manager import FileStateManager

if TYPE_CHECKING:
    from pathlib import Path


class SystemPhase(Enum):
    """Phase of the orchestration system."""

    INITIALIZING = auto()
    VALIDATING = auto()
    OPERATIONAL = auto()
    HALTED = auto()


@dataclass(frozen=True)
class SystemStatus:
    """Immutable snapshot of system status."""

    phase: SystemPhase
    conversations_handled: int
    last_coordinate: str | None
    integrity_verified: bool


class ThalobalOrchestrator:
    """Control-plane orchestrator handling lifecycle and state."""

    def __init__(self, storage_path: Path, seed: str = "thalos-babel-seed") -> None:
        """Initialize the orchestrator with storage path and seed."""
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
        """Initialize and validate the system."""
        self.phase = SystemPhase.VALIDATING
        self.validate()
        self.phase = SystemPhase.OPERATIONAL

    def validate(self) -> None:
        """Validate all system invariants."""
        results = self.validator.validate_all()
        failures = [r for r in results if not r.passed]
        if failures:
            msg = f"Validation failed: {[f.message for f in failures]}"
            raise RuntimeError(msg)

    def get_status(self) -> SystemStatus:
        """Return current system status snapshot."""
        return SystemStatus(
            phase=self.phase,
            conversations_handled=self.state.conversations_handled,
            last_coordinate=self.state.last_coordinate,
            integrity_verified=self.state.integrity_verified,
        )

    def checkpoint(self) -> Path:
        """Create a deterministic checkpoint of system state."""
        return self.checkpoint_manager.create(self.state)

    def reconcile(self) -> None:
        """Reconcile and resolve any state inconsistencies."""
        inconsistencies = self.reconciler.check_state(self.state.last_coordinate)
        self.reconciler.resolve(inconsistencies)

    def terminate(self) -> None:
        """Terminate the system and halt the lifecycle."""
        self.phase = SystemPhase.HALTED

    def _record_state(self, coordinate: str) -> None:
        self.state = self.state_manager.record_conversation(self.state, coordinate)

    def _ensure_storage_layout(self) -> None:
        for sub in ("conversations", "coordinates", "audit"):
            target = self.storage_path / sub
            target.mkdir(parents=True, exist_ok=True)
