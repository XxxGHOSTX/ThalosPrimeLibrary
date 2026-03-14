"""Persistent state management for Babel subsystem."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class SystemState:
    """Serializable system state for the Babel subsystem."""

    version: str
    conversations_handled: int
    session_turns: dict[str, int]
    last_coordinate: str | None
    integrity_verified: bool


class FileStateManager:
    """Persist deterministic state to disk."""

    def __init__(self, base_dir: Path) -> None:
        """Initialize file state manager.

        Args:
            base_dir: Base directory for state storage.

        """
        self.base_dir = base_dir
        self.state_path = self.base_dir / "state" / "current_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "state").mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        """Initialize state directory structure."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "state").mkdir(parents=True, exist_ok=True)

    def validate(self) -> None:
        """Validate that the state directory is accessible."""
        if not self.base_dir.exists():
            msg = f"State directory does not exist: {self.base_dir}"
            raise RuntimeError(msg)

    def operate(self) -> None:
        """Execute primary work: load and verify current state."""
        self.load()

    def reconcile(self) -> None:
        """Reconcile state directory to consistent condition."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "state").mkdir(parents=True, exist_ok=True)

    def checkpoint(self) -> None:
        """Serialize file state manager metadata (state file is already on disk)."""

    def terminate(self) -> None:
        """Clean up file state manager resources."""

    def load(self) -> SystemState:
        """Load system state from disk.

        Returns:
            Loaded SystemState, or a default state if no file exists.

        """
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
        """Save system state to disk.

        Args:
            state: System state to persist.

        """
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")

    def next_turn_index(self, session_id: str, state: SystemState) -> int:
        """Return the next turn index for the given session.

        Args:
            session_id: Session identifier.
            state: Current system state to update in-place.

        Returns:
            Current turn index before increment.

        """
        current = state.session_turns.get(session_id, 0)
        state.session_turns[session_id] = current + 1
        return current

    def record_conversation(self, state: SystemState, coordinate: str) -> SystemState:
        """Record a new conversation and return updated state.

        Args:
            state: Current system state.
            coordinate: Coordinate string for the new conversation.

        Returns:
            Updated SystemState with incremented conversation count.

        """
        updated = SystemState(
            version=state.version,
            conversations_handled=state.conversations_handled + 1,
            session_turns=dict(state.session_turns),
            last_coordinate=coordinate,
            integrity_verified=state.integrity_verified,
        )
        self.save(updated)
        return updated
