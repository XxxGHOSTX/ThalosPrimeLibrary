"""Coherence validation for generated responses."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from thalos_prime.babel.core.context_hasher import ContextHasher

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoherenceReport:
    """Immutable result of a coherence validation check."""

    is_coherent: bool
    violations: list[str]


class LinguisticCoherenceValidator:
    """Ensure responses meet minimal coherence guarantees."""

    MIN_LENGTH = 8

    def validate(self, text: str) -> CoherenceReport:
        """Validate text coherence and return a report with any violations found."""
        normalized = ContextHasher.normalize_text(text)
        violations: list[str] = []
        if len(normalized.split(" ")) < 2:
            violations.append("too_short")
        if not normalized.endswith((".", "!", "?")):
            violations.append("missing_terminal_punctuation")
        is_coherent = not violations and len(normalized) >= self.MIN_LENGTH
        return CoherenceReport(is_coherent=is_coherent, violations=violations)

    def initialize(self) -> None:
        """No-op initialization; LinguisticCoherenceValidator holds no mutable state."""
        _log.info("LinguisticCoherenceValidator initialized")

    def operate(self) -> None:
        """No-op operation phase; coherence checks are triggered via validate()."""

    def reconcile(self) -> None:
        """No-op reconciliation; LinguisticCoherenceValidator holds no mutable state."""

    def checkpoint(self) -> dict[str, object]:
        """Return a snapshot of validator configuration."""
        return {"min_length": self.MIN_LENGTH}

    def terminate(self) -> None:
        """No-op termination; LinguisticCoherenceValidator holds no mutable state."""
        _log.info("LinguisticCoherenceValidator terminated")
