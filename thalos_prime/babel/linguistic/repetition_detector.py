"""Detect repetition within a session."""

from __future__ import annotations

from thalos_prime.babel.core.context_hasher import ContextHasher


class RepetitionDetector:
    """Detect repeated inputs deterministically."""

    def __init__(self) -> None:
        """Initialize an empty repetition cache keyed by session id."""
        self._session_hashes: dict[str, set[str]] = {}

    def record(self, session_id: str, user_input: str) -> bool:
        """Record *user_input* for *session_id* and report whether it repeats.

        Args:
            session_id: Deterministic session identifier.
            user_input: Raw user input.

        Returns:
            True if the input was previously seen for the session, else False.

        """
        fingerprint = ContextHasher.hash_text(user_input)
        seen = self._session_hashes.setdefault(session_id, set())
        is_repeat = fingerprint in seen
        seen.add(fingerprint)
        return is_repeat
