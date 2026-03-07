"""Semantic invariants and validation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .semantic_frames import SemanticFrame

_log = logging.getLogger(__name__)


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

    def initialize(self) -> None:
        """No-op initialization; SemanticInvariantChecker holds no mutable state."""
        _log.info("SemanticInvariantChecker initialized")

    def operate(self) -> None:
        """No-op operation phase; invariant checks are triggered via validate()."""

    def reconcile(self) -> None:
        """No-op reconciliation; SemanticInvariantChecker holds no mutable state."""

    def checkpoint(self) -> dict[str, object]:
        """Return an empty snapshot; SemanticInvariantChecker carries no persisted state."""
        return {}

    def terminate(self) -> None:
        """No-op termination; SemanticInvariantChecker holds no mutable state."""
        _log.info("SemanticInvariantChecker terminated")
