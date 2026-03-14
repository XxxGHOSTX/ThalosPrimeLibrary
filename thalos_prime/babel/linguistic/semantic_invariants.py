"""Semantic invariants and validation.

Ensures semantic preservation across response generation frames.

Data Plane: semantic checks only; no lifecycle coordination logic.
"""

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
    """Validate semantic preservation for frames.

    Implements the six-method lifecycle contract so that it may participate
    in lifecycle-managed subsystems.
    """

    def initialize(self) -> None:
        """No-op initialiser; SemanticInvariantChecker is stateless."""

    def operate(self) -> None:
        """No-op operate; this checker has no background work."""

    def reconcile(self) -> None:
        """No-op reconcile; this checker holds no mutable state."""

    def checkpoint(self) -> dict[str, object]:
        """Return an empty checkpoint; this checker is stateless.

        Returns:
            Dict identifying the component.

        """
        return {"component": "SemanticInvariantChecker"}

    def terminate(self) -> None:
        """No-op terminate; this checker holds no resources."""

    def validate(self, frame: SemanticFrame) -> bool:
        """Return True when *frame* preserves its semantic invariants.

        Preservation requires a non-empty topic and a non-empty fingerprint.

        Args:
            frame: Semantic frame to check.

        Returns:
            True when the semantic core has both a non-empty topic and fingerprint.

        """
        return bool(frame.semantic_core.topic) and bool(frame.semantic_core.fingerprint)
