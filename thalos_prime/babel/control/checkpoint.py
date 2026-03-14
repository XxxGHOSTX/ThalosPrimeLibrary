"""Checkpoint management for Babel subsystem.

Creates deterministic, versioned checkpoints of system state to disk.

Data Plane: state serialisation only; no lifecycle coordination logic.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .state_manager import SystemState


class CheckpointManager:
    """Create deterministic checkpoints of system state.

    Checkpoints are written as JSON files named by conversation count.
    All operations are idempotent; the checkpoint directory is created on
    demand.
    """

    def __init__(self, base_dir: Path) -> None:
        """Initialize with *base_dir* as the storage root.

        Args:
            base_dir: Root directory under which ``state/checkpoints/`` is created.

        """
        self.checkpoint_dir: Path = base_dir / "state" / "checkpoints"
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle contract
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Create the checkpoint directory and mark as initialized."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True

    def validate(self) -> bool:
        """Return True when the checkpoint directory exists.

        Returns:
            True if the checkpoint directory is present on disk.

        """
        return self.checkpoint_dir.exists()

    def operate(self) -> None:
        """Ensure the checkpoint directory exists (idempotent)."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def reconcile(self) -> None:
        """Re-create the checkpoint directory if it was removed."""
        if not self.checkpoint_dir.exists():
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def checkpoint(self) -> dict[str, object]:
        """Return a serializable snapshot of this manager's state.

        Returns:
            Dict with ``component``, ``checkpoint_dir``, and ``initialized`` fields.

        """
        return {
            "component": "CheckpointManager",
            "checkpoint_dir": str(self.checkpoint_dir),
            "initialized": self._initialized,
        }

    def terminate(self) -> None:
        """Mark as uninitialized; does not remove checkpoint files."""
        self._initialized = False

    # ------------------------------------------------------------------
    # Domain operations
    # ------------------------------------------------------------------

    def create(self, state: SystemState) -> Path:
        """Write *state* as a JSON checkpoint file.

        Args:
            state: Current system state to persist.

        Returns:
            Path to the written checkpoint file.

        """
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        filename = f"checkpoint_{state.conversations_handled}.json"
        path = self.checkpoint_dir / filename
        path.write_text(_state_to_json(state), encoding="utf-8")
        return path


def _state_to_json(state: SystemState) -> str:
    """Serialize *state* to a JSON string.

    Args:
        state: System state dataclass instance.

    Returns:
        Pretty-printed JSON string.

    """
    return json.dumps(asdict(state), indent=2)
