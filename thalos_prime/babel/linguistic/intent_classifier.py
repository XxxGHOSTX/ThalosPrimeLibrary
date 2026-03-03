"""Deterministic intent classification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Final

from thalos_prime.babel.core.context_hasher import ContextHasher


class Intent(Enum):
    """User intent categories."""

    QUESTION = auto()
    STATEMENT = auto()
    ACKNOWLEDGMENT = auto()


@dataclass(frozen=True)
class IntentAnalysis:
    """Result of intent classification."""

    intent: Intent
    topic_fingerprint: str


class DeterministicIntentClassifier:
    """Simple deterministic intent classifier."""

    QUESTION_MARK: Final[str] = "?"

    def classify(self, user_input: str) -> IntentAnalysis:
        """Classify user intent from input text."""
        normalized = ContextHasher.normalize_text(user_input)
        if normalized.endswith(self.QUESTION_MARK):
            intent = Intent.QUESTION
        elif normalized in {"thanks", "thank you", "ok", "ack"}:
            intent = Intent.ACKNOWLEDGMENT
        else:
            intent = Intent.STATEMENT
        topic_fingerprint = ContextHasher.hash_text(normalized)[:16]
        return IntentAnalysis(intent=intent, topic_fingerprint=topic_fingerprint)
