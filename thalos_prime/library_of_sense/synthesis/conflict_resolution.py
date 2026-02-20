"""Library of Sense - Conflict Resolution.

Resolves conflicting information from multiple retrieval sources using
majority voting and confidence-weighted consensus.
"""

from __future__ import annotations

import logging

from thalos_prime.library_of_sense.core.interfaces import (
    QueryContext,
    RetrievalResult,
    SynthesisResult,
)

logger = logging.getLogger(__name__)


class ConflictResolver:
    """Resolves conflicts between retrieval results using majority voting.

    Groups results by content similarity and selects the group with the
    highest total confidence as the consensus answer.
    """

    def _group_similar(
        self,
        results: list[RetrievalResult],
    ) -> list[list[RetrievalResult]]:
        """Group results by content similarity using word overlap.

        Args:
            results: List of results to group.

        Returns:
            List of groups, each containing similar RetrievalResult instances.

        """
        groups: list[list[RetrievalResult]] = []
        for result in results:
            placed = False
            result_words = set(result.content.lower().split())
            for group in groups:
                rep = group[0]
                rep_words = set(rep.content.lower().split())
                if result_words & rep_words:
                    group.append(result)
                    placed = True
                    break
            if not placed:
                groups.append([result])
        return groups

    def synthesize(
        self,
        results: list[RetrievalResult],
        context: QueryContext,
    ) -> SynthesisResult:
        """Resolve conflicts and produce a consensus synthesis result.

        Args:
            results: List of possibly conflicting retrieval results.
            context: Query context providing domain and options.

        Returns:
            SynthesisResult representing the consensus answer.

        """
        _ = context
        if not results:
            return SynthesisResult(answer="", confidence=0.0, sources=[])

        non_empty = [r for r in results if r.content.strip()]
        if not non_empty:
            return SynthesisResult(answer="", confidence=0.0, sources=results)

        groups = self._group_similar(non_empty)
        best_group = max(
            groups,
            key=lambda g: sum(r.confidence for r in g),
        )

        best_result = max(best_group, key=lambda r: r.confidence)
        group_confidence = sum(r.confidence for r in best_group) / len(best_group)

        steps = [
            f"Grouped {len(non_empty)} results into {len(groups)} conflict clusters",
            f"Resolved conflict: selected cluster of {len(best_group)} agreeing results",
        ]

        return SynthesisResult(
            answer=best_result.content,
            confidence=min(group_confidence, 1.0),
            sources=best_group,
            reasoning_steps=steps,
        )


__all__ = ["ConflictResolver"]
