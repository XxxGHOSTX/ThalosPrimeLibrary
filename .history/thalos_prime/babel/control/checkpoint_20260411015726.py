"""Checkpoint management for Babel subsystem."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from .state_manager import SystemState


class CheckpointManager:
    """Create deterministic checkpoints of system state."""

    def __init__(self, base_dir: Path) -> None:
        self.checkpoint_dir = base_dir / "state" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create(self, state: SystemState) -> Path:
        filename = f"checkpoint_{state.conversations_handled}.json"
        path = self.checkpoint_dir / filename
        path.write_text(pathlib_json(state), encoding="utf-8")
        return path

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic manager state surface."""
        return {
            "checkpoint_dir": str(self.checkpoint_dir),
        }

    def checkpoint(self) -> dict[str, Any]:
        """Return checkpoint payload for validator/tooling surfaces."""
        return {
            "schema_version": "1.0",
            "manager": self.to_dict(),
        }


def pathlib_json(state: SystemState) -> str:
    return json.dumps(asdict(state), indent=2)
