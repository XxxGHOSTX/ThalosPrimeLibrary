"""Coherence validation for generated responses."""

from __future__ import annotations

from dataclasses import dataclass

from thalos_prime.babel.core.context_hasher import ContextHasher


@dataclass(frozen=True)
class CoherenceReport:
    """Report of coherence validation for a generated response."""

    is_coherent: bool
    violations: list[str]


class LinguisticCoherenceValidator:
    """Ensure responses meet minimal coherence guarantees."""

    MIN_LENGTH = 8

    def initialize(self) -> None:
        """Initialize the validator (stateless; no-op)."""

    def validate(self, text: str) -> CoherenceReport:
        """Validate the coherence of a generated response.

        Args:
            text: The response text to validate.

        Returns:
            CoherenceReport with is_coherent flag and list of violations.

        """
        normalized = ContextHasher.normalize_text(text)
        violations: list[str] = []
        if len(normalized.split(" ")) < 2:
            violations.append("too_short")
        if not normalized.endswith((".", "!", "?")):
            violations.append("missing_terminal_punctuation")
        is_coherent = not violations and len(normalized) >= self.MIN_LENGTH
        return CoherenceReport(is_coherent=is_coherent, violations=violations)

    def operate(self) -> None:
        """Execute primary work (stateless validator; no-op)."""

    def reconcile(self) -> None:
        """Reconcile validator state (stateless; no-op)."""

    def checkpoint(self) -> None:
        """Serialize validator state (stateless; no state to serialize)."""

    def terminate(self) -> None:
        """Terminate the validator (stateless; no-op)."""
