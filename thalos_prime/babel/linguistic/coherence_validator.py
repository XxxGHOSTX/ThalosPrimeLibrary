"""Coherence validation for generated responses."""

from __future__ import annotations

from dataclasses import dataclass

from thalos_prime.babel.core.context_hasher import ContextHasher


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
