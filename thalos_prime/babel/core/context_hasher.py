"""Deterministic hashing helpers for Babel contexts.
"""

from __future__ import annotations

import re
from hashlib import sha256
from typing import Final


class ContextHasher:
    """Canonical hashing for inputs and coordinates."""

    _whitespace_pattern: Final[re.Pattern[str]] = re.compile(r"\s+")

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Normalize text deterministically for hashing."""
        lowered = text.strip().lower()
        collapsed = cls._whitespace_pattern.sub(" ", lowered)
        return collapsed

    @classmethod
    def hash_text(cls, text: str) -> str:
        """Hash normalized text to a fixed digest."""
        normalized = cls.normalize_text(text)
        return sha256(normalized.encode("utf-8")).hexdigest()
