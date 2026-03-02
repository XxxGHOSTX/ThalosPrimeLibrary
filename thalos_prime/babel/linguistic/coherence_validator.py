"""
Coherence validation for generated responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..core.context_hasher import ContextHasher


@dataclass(frozen=True)
class CoherenceReport:
    is_coherent: bool
    violations: List[str]


class LinguisticCoherenceValidator:
    """Ensure responses meet minimal coherence guarantees."""

    MIN_LENGTH = 8

    def validate(self, text: str) -> CoherenceReport:
        normalized = ContextHasher.normalize_text(text)
        violations: List[str] = []
        if len(normalized.split(" ")) < 2:
            violations.append("too_short")
        if not normalized.endswith(('.', '!', '?')):
            violations.append("missing_terminal_punctuation")
        is_coherent = not violations and len(normalized) >= self.MIN_LENGTH
        return CoherenceReport(is_coherent=is_coherent, violations=violations)
