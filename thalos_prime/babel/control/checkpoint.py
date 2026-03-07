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
        """Initialize checkpoint directory under base_dir/state/checkpoints."""
        self.checkpoint_dir = base_dir / "state" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create(self, state: SystemState) -> Path:
        """Serialize state to a versioned checkpoint file and return its path."""
        filename = f"checkpoint_{state.conversations_handled}.json"
        path = self.checkpoint_dir / filename
        path.write_text(pathlib_json(state), encoding="utf-8")
        return path


def pathlib_json(state: SystemState) -> str:
    """Serialize a SystemState dataclass instance to a JSON string."""
    return json.dumps(asdict(state), indent=2)
