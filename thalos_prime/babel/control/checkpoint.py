"""Checkpoint management for Babel subsystem."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from .state_manager import SystemState

_log = logging.getLogger(__name__)


class CheckpointManager:
    """Create deterministic checkpoints of system state."""

    def __init__(self, base_dir: Path) -> None:
        """Initialize checkpoint directory under base_dir/state/checkpoints."""
        self.checkpoint_dir = base_dir / "state" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        """Ensure the checkpoint directory exists and is ready for use."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        _log.info("CheckpointManager initialized: dir=%s", self.checkpoint_dir)

    def validate(self) -> bool:
        """Return True if the checkpoint directory is accessible."""
        return self.checkpoint_dir.is_dir()

    def operate(self) -> None:
        """No-op operation phase; checkpoint creation is triggered via create()."""

    def reconcile(self) -> None:
        """Ensure checkpoint directory exists, recreating it if absent."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def checkpoint(self) -> dict[str, object]:
        """Return a snapshot of checkpoint manager state."""
        count = len(list(self.checkpoint_dir.glob("checkpoint_*.json")))
        return {"checkpoint_dir": str(self.checkpoint_dir), "checkpoint_count": count}

    def terminate(self) -> None:
        """No-op termination; checkpoint directory is preserved for recovery."""
        _log.info("CheckpointManager terminated")

    def create(self, state: SystemState) -> Path:
        """Serialize state to a versioned checkpoint file and return its path."""
        filename = f"checkpoint_{state.conversations_handled}.json"
        path = self.checkpoint_dir / filename
        path.write_text(pathlib_json(state), encoding="utf-8")
        return path


def pathlib_json(state: SystemState) -> str:
    """Serialize a SystemState dataclass instance to a JSON string."""
    return json.dumps(asdict(state), indent=2)
