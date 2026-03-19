"""Library of Sense - Core Protocol Interfaces.

Defines fundamental protocols and data structures for all Library of Sense
subsystem components, enforcing strict typing and deterministic behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol, runtime_checkable


class QueryDomain(StrEnum):
    """Supported query domains for Library of Sense retrieval."""

    GENERAL = "general"
    MATHEMATICS = "mathematics"
    CODE = "code"
    WEB = "web"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    COMPUTATIONAL = "computational"


@dataclass
class QueryContext:
    """Query context providing domain hints and execution options."""

    domain: QueryDomain = QueryDomain.GENERAL
    require_proof: bool = False
    max_depth: int = 3
    timeout_seconds: float = 30.0
    seed: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, object]:
        """Serialize context to dictionary.

        Returns:
            Dictionary representation of this context.

        """
        return {
            "domain": self.domain.value,
            "require_proof": self.require_proof,
            "max_depth": self.max_depth,
            "timeout_seconds": self.timeout_seconds,
            "seed": self.seed,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RetrievalResult:
    """Result from a single retrieval source."""

    source: str
    content: str
    confidence: float
    metadata: dict[str, str] = field(default_factory=dict)
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this result.

        """
        return {
            "source": self.source,
            "content": self.content,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "retrieved_at": self.retrieved_at.isoformat(),
        }


@dataclass
class ValidationResult:
    """Result from a validation operation."""

    valid: bool
    message: str
    details: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this result.

        """
        return {
            "valid": self.valid,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class SynthesisResult:
    """Result from a knowledge synthesis operation."""

    answer: str
    confidence: float
    sources: list[RetrievalResult] = field(default_factory=list)
    reasoning_steps: list[str] = field(default_factory=list)
    verified: bool = False

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this result.

        """
        return {
            "answer": self.answer,
            "confidence": self.confidence,
            "sources": [s.to_dict() for s in self.sources],
            "reasoning_steps": self.reasoning_steps,
            "verified": self.verified,
        }


@dataclass
class ReasoningResult:
    """Result from a reasoning operation."""

    conclusion: str
    proof_steps: list[str]
    valid: bool
    confidence: float

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this result.

        """
        return {
            "conclusion": self.conclusion,
            "proof_steps": self.proof_steps,
            "valid": self.valid,
            "confidence": self.confidence,
        }


@runtime_checkable
class RetrievalSource(Protocol):
    """Protocol for all retrieval source implementations."""

    def query(self, query: str, context: QueryContext) -> RetrievalResult:
        """Execute a retrieval query against this source.

        Args:
            query: The query string to search for.
            context: Query context with domain and execution options.

        Returns:
            RetrievalResult containing the retrieved content.

        """
        ...

    def validate(self) -> ValidationResult:
        """Validate this retrieval source configuration.

        Returns:
            ValidationResult indicating whether the source is correctly configured.

        """
        ...

    def initialize(self) -> None:
        """Initialize this retrieval source and prepare resources."""
        ...

    def operate(self) -> None:
        """Transition this source to active operating state."""
        ...

    def reconcile(self) -> None:
        """Reconcile source state to ensure consistency."""
        ...

    def checkpoint(self) -> object:
        """Emit a checkpoint log of current source state.

        Returns:
            Optional serialized state dict, or None if not applicable.

        """
        ...

    def terminate(self) -> None:
        """Terminate this source and release resources."""
        ...


@runtime_checkable
class KnowledgeSynthesizer(Protocol):
    """Protocol for knowledge synthesis components."""

    def synthesize(
        self,
        results: list[RetrievalResult],
        context: QueryContext,
    ) -> SynthesisResult:
        """Synthesize knowledge from multiple retrieval results.

        Args:
            results: List of retrieval results to synthesize.
            context: Query context guiding synthesis.

        Returns:
            SynthesisResult with the synthesized answer.

        """
        ...


@runtime_checkable
class ReasoningEngine(Protocol):
    """Protocol for reasoning engine implementations."""

    def reason(
        self,
        premise: str,
        context: QueryContext,
    ) -> ReasoningResult:
        """Apply reasoning to derive conclusions from a premise.

        Args:
            premise: The statement or expression to reason about.
            context: Query context providing reasoning options.

        Returns:
            ReasoningResult with conclusions and proof steps.

        """
        ...


__all__ = [
    "KnowledgeSynthesizer",
    "QueryContext",
    "QueryDomain",
    "ReasoningEngine",
    "ReasoningResult",
    "RetrievalResult",
    "RetrievalSource",
    "SynthesisResult",
    "ValidationResult",
]
