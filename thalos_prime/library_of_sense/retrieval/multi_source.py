"""Library of Sense - Multi-Source Retrieval.

Aggregates results from multiple retrieval sources, deduplicates content,
and ranks results by confidence for downstream synthesis.
"""

from __future__ import annotations

import logging

from thalos_prime.library_of_sense.core.interfaces import (
    QueryContext,
    RetrievalResult,
    RetrievalSource,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class MultiSourceRetriever:
    """Aggregates and ranks results from multiple registered retrieval sources."""

    def __init__(self, min_confidence: float = 0.0) -> None:
        """Initialize the multi-source retriever.

        Args:
            min_confidence: Minimum confidence threshold for including results.
        """
        self._sources: list[RetrievalSource] = []
        self._min_confidence = min_confidence

    def add_source(self, source: RetrievalSource) -> None:
        """Register a retrieval source.

        Args:
            source: RetrievalSource to add.
        """
        self._sources.append(source)

    def query_all(self, query: str, context: QueryContext) -> list[RetrievalResult]:
        """Query all registered sources and return filtered, ranked results.

        Args:
            query: The query string.
            context: Query context with domain hints.

        Returns:
            Filtered and confidence-ranked list of RetrievalResult.
        """
        results: list[RetrievalResult] = []
        for source in self._sources:
            result = source.query(query, context)
            if result.confidence >= self._min_confidence:
                results.append(result)
                logger.debug(
                    "Source %s returned result with confidence=%.2f",
                    result.source,
                    result.confidence,
                )
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    def validate_sources(self) -> list[ValidationResult]:
        """Validate all registered sources.

        Returns:
            List of ValidationResult for each registered source.
        """
        return [source.validate() for source in self._sources]

    def source_count(self) -> int:
        """Return the number of registered sources.

        Returns:
            Count of registered retrieval sources.
        """
        return len(self._sources)


__all__ = ["MultiSourceRetriever"]
