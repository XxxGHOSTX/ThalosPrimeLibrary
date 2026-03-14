"""Detect repetition within a session."""

from __future__ import annotations

from thalos_prime.babel.core.context_hasher import ContextHasher


class RepetitionDetector:
    """Detect repeated inputs deterministically."""

    def __init__(self) -> None:
        """Initialise an empty session-level repetition tracker."""
        self._session_hashes: dict[str, set[str]] = {}

    def record(self, session_id: str, user_input: str) -> bool:
        """Record *user_input* for *session_id*; return True if it was already seen."""
        fingerprint = ContextHasher.hash_text(user_input)
        seen = self._session_hashes.setdefault(session_id, set())
        is_repeat = fingerprint in seen
        seen.add(fingerprint)
        return is_repeat
