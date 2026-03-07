"""Persistent state management for Babel subsystem."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)


@dataclass
class SystemState:
    """Mutable system state persisted between orchestrator invocations."""

    version: str
    conversations_handled: int
    session_turns: dict[str, int]
    last_coordinate: str | None
    integrity_verified: bool


class FileStateManager:
    """Persist deterministic state to disk."""

    def __init__(self, base_dir: Path) -> None:
        """Initialize the state manager and ensure storage directories exist."""
        self.base_dir = base_dir
        self.state_path = self.base_dir / "state" / "current_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "state").mkdir(parents=True, exist_ok=True)

    def load(self) -> SystemState:
        """Load state from disk, returning a default state if none exists."""
        if not self.state_path.exists():
            return SystemState(
                version="1.0.0",
                conversations_handled=0,
                session_turns={},
                last_coordinate=None,
                integrity_verified=True,
            )
        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        return SystemState(**raw)

    def save(self, state: SystemState) -> None:
        """Persist state to disk as JSON."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")

    def next_turn_index(self, session_id: str, state: SystemState) -> int:
        """Return the current turn index for the session and increment it in-place."""
        current = state.session_turns.get(session_id, 0)
        state.session_turns[session_id] = current + 1
        return current

    def record_conversation(self, state: SystemState, coordinate: str) -> SystemState:
        """Return an updated state with conversation count incremented and coordinate recorded."""
        updated = SystemState(
            version=state.version,
            conversations_handled=state.conversations_handled + 1,
            session_turns=dict(state.session_turns),
            last_coordinate=coordinate,
            integrity_verified=state.integrity_verified,
        )
        self.save(updated)
        return updated

    def initialize(self) -> None:
        """Ensure storage directories exist and log readiness."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "state").mkdir(parents=True, exist_ok=True)
        _log.info("FileStateManager initialized: base_dir=%s", self.base_dir)

    def validate(self) -> bool:
        """Return True if the state directory is accessible."""
        return self.state_path.parent.is_dir()

    def operate(self) -> None:
        """No-op operation phase; state updates are triggered via record_conversation()."""

    def reconcile(self) -> None:
        """Ensure storage directories exist, recreating them if absent."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "state").mkdir(parents=True, exist_ok=True)

    def checkpoint(self) -> dict[str, object]:
        """Return a snapshot of the state manager configuration."""
        return {
            "base_dir": str(self.base_dir),
            "state_path": str(self.state_path),
            "state_exists": self.state_path.exists(),
        }

    def terminate(self) -> None:
        """No-op termination; state file is preserved on disk for recovery."""
        _log.info("FileStateManager terminated")
