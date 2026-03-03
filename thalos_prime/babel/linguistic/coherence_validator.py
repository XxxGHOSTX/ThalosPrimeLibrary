"""Coherence validation for generated responses."""

from __future__ import annotations

from dataclasses import dataclass

from thalos_prime.babel.core.context_hasher import ContextHasher


@dataclass(frozen=True)
class CoherenceReport:
    """Coherence validation report."""

    is_coherent: bool
    violations: list[str]


class LinguisticCoherenceValidator:
    """Validate linguistic coherence of responses."""

    MIN_LENGTH: int = 8
    MIN_WORD_COUNT: int = 2

    def validate(self, text: str) -> CoherenceReport:
        """Validate coherence of the given text."""
        normalized = ContextHasher.normalize_text(text)
        violations: list[str] = []
        if len(normalized.split(" ")) < self.MIN_WORD_COUNT:
            violations.append("too_short")
        if not normalized.endswith((".", "!", "?")):
            violations.append("missing_terminal_punctuation")
        is_coherent = not violations and len(normalized) >= self.MIN_LENGTH
        return CoherenceReport(is_coherent=is_coherent, violations=violations)
