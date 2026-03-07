"""Semantic invariants and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .semantic_frames import SemanticFrame


@dataclass(frozen=True)
class SemanticCore:
    """Minimal semantic fingerprint for a response."""

    topic: str
    fingerprint: str


class SemanticInvariantChecker:
    """Validate semantic preservation for frames."""

    def validate(self, frame: SemanticFrame) -> bool:
        """Return True if the frame's semantic core has a non-empty topic and fingerprint."""
        # In this deterministic slice, preservation means topic is non-empty and fingerprint exists.
        return bool(frame.semantic_core.topic) and bool(frame.semantic_core.fingerprint)
