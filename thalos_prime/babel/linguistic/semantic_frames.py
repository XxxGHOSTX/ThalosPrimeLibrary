"""Semantic frame construction for deterministic responses."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from thalos_prime.babel.core.context_hasher import ContextHasher

from .intent_classifier import DeterministicIntentClassifier, Intent, IntentAnalysis
from .semantic_invariants import SemanticCore


class FrameType(Enum):
    """Supported semantic frame categories."""

    DEFINITION = auto()
    ACKNOWLEDGMENT = auto()
    DESCRIPTION = auto()
    GENERIC = auto()


@dataclass(frozen=True)
class SemanticFrame:
    """Semantic frame holding core meaning and slot variables."""

    frame_type: FrameType
    semantic_core: SemanticCore
    variables: dict[str, str]

    def to_variables(self) -> dict[str, str]:
        """Return the slot variables for template filling."""
        return self.variables


class FrameConstructor:
    """Deterministically construct frames from user input."""

    def __init__(self, classifier: DeterministicIntentClassifier) -> None:
        """Initialize with an intent classifier."""
        self.classifier = classifier

    def construct(self, user_input: str) -> SemanticFrame:
        """Construct a :class:`SemanticFrame` for *user_input*."""
        analysis: IntentAnalysis = self.classifier.classify(user_input)
        normalized = ContextHasher.normalize_text(user_input)
        topic = normalized.rstrip("?")
        semantic_core = SemanticCore(topic=topic, fingerprint=analysis.topic_fingerprint)

        if analysis.intent == Intent.ACKNOWLEDGMENT:
            frame_type = FrameType.ACKNOWLEDGMENT
            variables = {"MESSAGE": "Acknowledged"}
        elif analysis.intent == Intent.QUESTION:
            frame_type = FrameType.DEFINITION
            variables = {"TOPIC": topic or "the topic", "DEFINIENDUM": topic or "item"}
        else:
            frame_type = FrameType.DESCRIPTION
            variables = {"SUBJECT": topic or "the subject", "DETAIL": "noted"}

        return SemanticFrame(
            frame_type=frame_type, semantic_core=semantic_core, variables=variables
        )
