"""Coherence validation for generated responses.

Ensures responses meet minimal linguistic coherence guarantees before delivery.

Data Plane: validation logic only; no lifecycle coordination.
"""

from __future__ import annotations

from dataclasses import dataclass

from thalos_prime.babel.core.context_hasher import ContextHasher

_MIN_WORD_COUNT: int = 2


@dataclass(frozen=True)
class CoherenceReport:
    """Result of a coherence validation check."""

    is_coherent: bool
    violations: list[str]


class LinguisticCoherenceValidator:
    """Ensure responses meet minimal coherence guarantees.

    Implements the six-method lifecycle contract so that it may participate
    in lifecycle-managed subsystems.
    """

    MIN_LENGTH: int = 8

    def initialize(self) -> None:
        """No-op initializer; LinguisticCoherenceValidator is stateless."""

    def operate(self) -> None:
        """No-op operate; this validator has no background work."""

    def reconcile(self) -> None:
        """No-op reconcile; this validator holds no mutable state."""

    def checkpoint(self) -> dict[str, object]:
        """Return an empty checkpoint; this validator is stateless.

        Returns:
            Dict identifying the component.

        """
        return {"component": "LinguisticCoherenceValidator"}

    def terminate(self) -> None:
        """No-op terminate; this validator holds no resources."""

    def validate(self, text: str) -> CoherenceReport:
        """Validate the linguistic coherence of *text*.

        Args:
            text: Response text to check.

        Returns:
            :class:`CoherenceReport` with ``is_coherent`` flag and list of violations.

        """
        normalized = ContextHasher.normalize_text(text)
        violations: list[str] = []
        if len(normalized.split(" ")) < _MIN_WORD_COUNT:
            violations.append("too_short")
        if not normalized.endswith((".", "!", "?")):
            violations.append("missing_terminal_punctuation")
        is_coherent = not violations and len(normalized) >= self.MIN_LENGTH
        return CoherenceReport(is_coherent=is_coherent, violations=violations)
