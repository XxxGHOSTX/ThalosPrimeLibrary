"""Library of Sense - Answer Generator.

Formats synthesized knowledge into structured, human-readable answers
with provenance metadata and reasoning trace.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from thalos_prime.library_of_sense.core.interfaces import (
        QueryContext,
        SynthesisResult,
    )

logger = logging.getLogger(__name__)


@dataclass
class StructuredAnswer:
    """A structured, human-readable answer with provenance and reasoning trace."""

    query: str
    answer: str
    confidence: float
    sources: list[str]
    reasoning_steps: list[str]
    verified: bool
    domain: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this structured answer.

        """
        return {
            "query": self.query,
            "answer": self.answer,
            "confidence": self.confidence,
            "sources": self.sources,
            "reasoning_steps": self.reasoning_steps,
            "verified": self.verified,
            "domain": self.domain,
            "generated_at": self.generated_at.isoformat(),
        }


class AnswerGenerator:
    """Formats synthesis results into StructuredAnswer objects with full provenance."""

    def generate(
        self,
        query: str,
        synthesis: SynthesisResult,
        context: QueryContext,
    ) -> StructuredAnswer:
        """Generate a structured answer from a synthesis result.

        Args:
            query: Original query string.
            synthesis: SynthesisResult to format.
            context: QueryContext providing domain information.

        Returns:
            StructuredAnswer with formatted content and provenance.

        """
        source_labels = [r.source for r in synthesis.sources]

        reasoning = list(synthesis.reasoning_steps)
        if synthesis.verified:
            reasoning.append("Answer verified against source content.")
        else:
            reasoning.append("Answer not verified; treat with lower confidence.")

        logger.info(
            "Generated answer: domain=%s confidence=%.2f sources=%d",
            context.domain.value,
            synthesis.confidence,
            len(source_labels),
        )

        return StructuredAnswer(
            query=query,
            answer=synthesis.answer,
            confidence=synthesis.confidence,
            sources=source_labels,
            reasoning_steps=reasoning,
            verified=synthesis.verified,
            domain=context.domain.value,
        )


__all__ = ["AnswerGenerator", "StructuredAnswer"]
