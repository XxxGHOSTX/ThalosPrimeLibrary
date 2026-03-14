"""Checkpoint management for Babel subsystem."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from .state_manager import SystemState


class CheckpointManager:
    """Create deterministic checkpoints of system state."""

    def __init__(self, base_dir: Path) -> None:
        """Initialize checkpoint manager.

        Args:
            base_dir: Base directory for checkpoint storage.

        """
        self.checkpoint_dir = base_dir / "state" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        """Initialize checkpoint directory structure."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> None:
        """Validate that the checkpoint directory exists and is writable."""
        if not self.checkpoint_dir.exists():
            msg = f"Checkpoint directory does not exist: {self.checkpoint_dir}"
            raise RuntimeError(msg)

    def operate(self) -> None:
        """Execute primary work (no-op for checkpoint manager)."""

    def reconcile(self) -> None:
        """Ensure checkpoint directory is consistent."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def checkpoint(self) -> None:
        """Serialize checkpoint manager state (no additional state to serialize)."""

    def terminate(self) -> None:
        """Clean up checkpoint manager resources."""

    def create(self, state: SystemState) -> Path:
        """Create a checkpoint file from the given state.

        Args:
            state: Current system state to checkpoint.

        Returns:
            Path to the created checkpoint file.

        """
        filename = f"checkpoint_{state.conversations_handled}.json"
        path = self.checkpoint_dir / filename
        path.write_text(pathlib_json(state), encoding="utf-8")
        return path


def pathlib_json(state: SystemState) -> str:
    """Serialize a SystemState to a JSON string.

    Args:
        state: The system state to serialize.

    Returns:
        JSON-formatted string representation of the state.

    """
    return json.dumps(asdict(state), indent=2)
