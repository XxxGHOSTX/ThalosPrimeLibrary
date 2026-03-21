"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

import uuid
from hashlib import sha256
import json
from datetime import datetime, timezone

from .seed_manager import ThalosSeedManager
from .state_store import ThalosStateStore


class ThalosSessionManager:
    """Multi-turn context and session lifecycle manager."""

    def __init__(self) -> None:
        """Initialize with seed manager and state store."""
        self.seed_manager = ThalosSeedManager()
        self.state_store = ThalosStateStore()
        self._sessions: dict[str, dict] = {}

    def create_session(self, context: dict | None = None) -> str:
        """Create a new session and derive its deterministic seed.

        Args:
            context: Optional initial context dict.

        Returns:
            The new session ID.
        """
        session_id = str(uuid.uuid4())
        seed = self.seed_manager.derive_execution_seed(context or {}, session_id)
        self._sessions[session_id] = {
            "id": session_id,
            "seed": seed,
            "context": context or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "turns": [],
        }
        state_hash = sha256(
            json.dumps(self._sessions[session_id], sort_keys=True).encode()
        ).hexdigest()
        self.state_store.write_event(session_id, "SESSION_CREATED", self._sessions[session_id], state_hash)
        return session_id

    def add_turn(self, session_id: str, role: str, content: str) -> str:
        """Append a conversation turn to an existing session.

        Args:
            session_id: The session to update.
            role: The speaker role (e.g. "user", "assistant").
            content: The message content.

        Returns:
            The SHA-256 state hash of the new turn.

        Raises:
            KeyError: If the session does not exist.
        """
        if session_id not in self._sessions:
            raise KeyError(f"Session {session_id} not found")
        turn = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._sessions[session_id]["turns"].append(turn)
        state_hash = sha256(json.dumps(turn, sort_keys=True).encode()).hexdigest()
        self.state_store.write_event(session_id, "TURN_ADDED", turn, state_hash)
        return state_hash

    def get_session(self, session_id: str) -> dict | None:
        """Retrieve a session by ID, or None if not found."""
        return self._sessions.get(session_id)
