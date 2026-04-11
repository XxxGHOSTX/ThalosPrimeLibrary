"""Detect repetition within a session."""

from __future__ import annotations

from thalos_prime.babel.core.context_hasher import ContextHasher


class RepetitionDetector:
    """Detect repeated inputs deterministically."""

    def __init__(self) -> None:
        self._session_hashes: dict[str, set[str]] = {}

    def record(self, session_id: str, user_input: str) -> bool:
        fingerprint = ContextHasher.hash_text(user_input)
        seen = self._session_hashes.setdefault(session_id, set())
        is_repeat = fingerprint in seen
        seen.add(fingerprint)
        return is_repeat
