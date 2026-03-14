"""Persistent state management for Babel subsystem.

Provides deterministic JSON-backed state persistence.

Data Plane: state I/O only; no lifecycle coordination logic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SystemState:
    """Versioned system state for the Babel subsystem."""

    version: str
    conversations_handled: int
    session_turns: dict[str, int]
    last_coordinate: str | None
    integrity_verified: bool


class FileStateManager:
    """Persist deterministic state to disk as versioned JSON.

    All mutations return a new :class:`SystemState` instance; the manager
    itself is stateless with respect to the content it persists.
    """

    def __init__(self, base_dir: Path) -> None:
        """Initialize with *base_dir* as the storage root.

        Args:
            base_dir: Root directory for state storage.

        """
        self.base_dir: Path = base_dir
        self.state_path: Path = self.base_dir / "state" / "current_state.json"
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle contract
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Create required directories and mark as initialized."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "state").mkdir(parents=True, exist_ok=True)
        self._initialized = True

    def validate(self) -> bool:
        """Return True when the storage directory exists.

        Returns:
            True if the base directory is present.

        """
        return self.base_dir.exists()

    def operate(self) -> None:
        """Ensure storage directories exist (idempotent)."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "state").mkdir(parents=True, exist_ok=True)

    def reconcile(self) -> None:
        """Re-create storage directories if they were removed."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "state").mkdir(parents=True, exist_ok=True)

    def checkpoint(self) -> dict[str, object]:
        """Return a serializable snapshot of this manager's state.

        Returns:
            Dict with ``component``, ``state_path``, and ``initialized`` fields.

        """
        return {
            "component": "FileStateManager",
            "state_path": str(self.state_path),
            "initialized": self._initialized,
        }

    def terminate(self) -> None:
        """Mark as uninitialized; does not remove persisted state."""
        self._initialized = False

    # ------------------------------------------------------------------
    # Domain operations
    # ------------------------------------------------------------------

    def load(self) -> SystemState:
        """Load state from disk, returning a default if none exists.

        Returns:
            Loaded or default :class:`SystemState`.

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
        """Persist *state* to disk.

        Args:
            state: System state to write.

        """
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")

    def next_turn_index(self, session_id: str, state: SystemState) -> int:
        """Return and increment the turn index for *session_id*.

        Args:
            session_id: Session identifier.
            state: Current system state (mutated in place).

        Returns:
            Previous turn index for the session.

        """
        current = state.session_turns.get(session_id, 0)
        state.session_turns[session_id] = current + 1
        return current

    def record_conversation(self, state: SystemState, coordinate: str) -> SystemState:
        """Return a new state with conversation count incremented.

        Args:
            state: Current system state.
            coordinate: Coordinate string for the completed conversation.

        Returns:
            Updated :class:`SystemState` persisted to disk.

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
