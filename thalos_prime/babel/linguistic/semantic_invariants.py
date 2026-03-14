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

    def initialize(self) -> None:
        """Initialize the checker (stateless; no-op)."""

    def validate(self, frame: SemanticFrame) -> bool:
        """Validate semantic invariants for the given frame.

        Args:
            frame: The semantic frame to validate.

        Returns:
            True if topic is non-empty and fingerprint exists.

        """
        return bool(frame.semantic_core.topic) and bool(frame.semantic_core.fingerprint)

    def operate(self) -> None:
        """Execute primary work (stateless checker; no-op)."""

    def reconcile(self) -> None:
        """Reconcile checker state (stateless; no-op)."""

    def checkpoint(self) -> None:
        """Serialize checker state (stateless; no state to serialize)."""

    def terminate(self) -> None:
        """Terminate the checker (stateless; no-op)."""
