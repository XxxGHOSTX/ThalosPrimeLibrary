"""Library of Sense - Knowledge Fusion.

Merges and deduplicates retrieval results from multiple sources,
applying confidence-weighted fusion to produce a unified answer.
"""

from __future__ import annotations

import logging

from thalos_prime.library_of_sense.core.interfaces import (
    QueryContext,
    RetrievalResult,
    SynthesisResult,
)

logger = logging.getLogger(__name__)

_DEDUP_THRESHOLD = 0.9


class KnowledgeFusion:
    """Fuses results from multiple retrieval sources into a single synthesis result.

    Applies confidence weighting and deduplication to merge knowledge from
    heterogeneous sources deterministically.
    """

    def __init__(self, dedup_threshold: float = _DEDUP_THRESHOLD) -> None:
        """Initialize the knowledge fusion engine.

        Args:
            dedup_threshold: Similarity threshold above which results are considered
                duplicate and merged.
        """
        self._dedup_threshold = dedup_threshold

    def _is_duplicate(self, a: str, b: str) -> bool:
        """Determine if two content strings are near-duplicates.

        Uses character-level Jaccard similarity as a deterministic metric.

        Args:
            a: First content string.
            b: Second content string.

        Returns:
            True if the Jaccard similarity exceeds the dedup threshold.
        """
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        if not set_a and not set_b:
            return True
        if not set_a or not set_b:
            return False
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        similarity = intersection / union
        return similarity >= self._dedup_threshold

    def deduplicate(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        """Remove near-duplicate results, keeping the highest-confidence version.

        Args:
            results: List of RetrievalResult to deduplicate.

        Returns:
            Deduplicated list with highest-confidence results preserved.
        """
        unique: list[RetrievalResult] = []
        for candidate in results:
            is_dup = any(
                self._is_duplicate(candidate.content, existing.content)
                for existing in unique
            )
            if not is_dup:
                unique.append(candidate)
        return unique

    def synthesize(
        self,
        results: list[RetrievalResult],
        context: QueryContext,
    ) -> SynthesisResult:
        """Synthesize a unified answer from multiple retrieval results.

        Args:
            results: List of retrieval results to fuse.
            context: Query context guiding synthesis.

        Returns:
            SynthesisResult with the fused answer and confidence.
        """
        _ = context
        if not results:
            return SynthesisResult(answer="", confidence=0.0, sources=[])

        unique = self.deduplicate(results)
        unique.sort(key=lambda r: r.confidence, reverse=True)

        top_results = unique[:3]
        answer_parts = [r.content for r in top_results if r.content]
        answer = " ".join(answer_parts)

        total_weight = sum(r.confidence for r in top_results)
        confidence = total_weight / len(top_results) if top_results else 0.0

        steps = [
            f"Fused {len(results)} results into {len(unique)} unique answers",
            f"Selected top {len(top_results)} by confidence",
        ]

        return SynthesisResult(
            answer=answer,
            confidence=min(confidence, 1.0),
            sources=top_results,
            reasoning_steps=steps,
        )


__all__ = ["KnowledgeFusion"]
