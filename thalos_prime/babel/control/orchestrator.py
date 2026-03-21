"""Base orchestrator for Babel subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from thalos_prime.babel.core.validation import SystemValidator

from .checkpoint import CheckpointManager
from .reconciler import Reconciler
from .state_manager import FileStateManager, SystemState


class SystemPhase(Enum):
    """Lifecycle phase of the orchestrator."""

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
        """Initialize with *storage_path* and deterministic *seed*."""
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
        """Transition to VALIDATING, run validation, then set OPERATIONAL."""
        self.phase = SystemPhase.VALIDATING
        self.validate()
        self.phase = SystemPhase.OPERATIONAL

    def validate(self) -> None:
        """Run all registered validators and raise on any failure."""
        results = self.validator.validate_all()
        failures = [r for r in results if not r.passed]
        if failures:
            messages = [f.message for f in failures]
            msg = f"Validation failed: {messages}"
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
        """Write and return the path of the current state checkpoint."""
        return self.checkpoint_manager.create(self.state)

    def operate(self) -> None:
        """Execute primary orchestration work: reconcile state and log status."""
        self.reconcile()

    def reconcile(self) -> None:
        """Detect and resolve state inconsistencies via the Reconciler."""
        inconsistencies = self.reconciler.check_state(self.state.last_coordinate)
        self.reconciler.resolve(inconsistencies)

    def terminate(self) -> None:
        """Set phase to HALTED, releasing the orchestrator from operation."""
        self.phase = SystemPhase.HALTED

    def _record_state(self, coordinate: str) -> None:
        self.state = self.state_manager.record_conversation(self.state, coordinate)

    def _ensure_storage_layout(self) -> None:
        for sub in ("conversations", "coordinates", "audit"):
            target = self.storage_path / sub
            target.mkdir(parents=True, exist_ok=True)
