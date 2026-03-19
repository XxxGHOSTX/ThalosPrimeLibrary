"""Library of Sense - Response Builder.

Constructs structured API response dictionaries from StructuredAnswer
and SynthesisResult objects with versioned schema.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from thalos_prime.library_of_sense.synthesis.answer_generator import StructuredAnswer

logger = logging.getLogger(__name__)

_SCHEMA_VERSION: Final[str] = "1.0"


class ResponseBuilder:
    """Builds versioned, structured API response dictionaries.

    Converts StructuredAnswer objects into dict responses with a fixed
    schema version for forward-compatible serialization.
    """

    def build(self, answer: StructuredAnswer) -> dict[str, object]:
        """Build a structured API response from a StructuredAnswer.

        Args:
            answer: StructuredAnswer to serialize into a response.

        Returns:
            Dictionary with versioned response schema.

        """
        return {
            "schema_version": _SCHEMA_VERSION,
            "query": answer.query,
            "answer": answer.answer,
            "confidence": answer.confidence,
            "verified": answer.verified,
            "domain": answer.domain,
            "sources": answer.sources,
            "reasoning_steps": answer.reasoning_steps,
            "generated_at": answer.generated_at.isoformat(),
            "response_at": datetime.now(timezone.utc).isoformat(),
        }

    def build_error(self, query: str, message: str) -> dict[str, object]:
        """Build a structured error response.

        Args:
            query: Original query string.
            message: Error message describing the failure.

        Returns:
            Dictionary with error response schema.

        """
        logger.error("ResponseBuilder: error for query %r: %s", query, message)
        return {
            "schema_version": _SCHEMA_VERSION,
            "query": query,
            "error": message,
            "response_at": datetime.now(timezone.utc).isoformat(),
        }


__all__ = ["ResponseBuilder"]
