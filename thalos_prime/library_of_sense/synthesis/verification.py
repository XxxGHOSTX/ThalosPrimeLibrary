"""Library of Sense - Result Verification.

Verifies synthesized answers for consistency and factual grounding
by cross-checking against source content.
"""

from __future__ import annotations

import logging

from thalos_prime.library_of_sense.core.interfaces import (
    RetrievalResult,
    SynthesisResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)

_MIN_VERIFIED_CONFIDENCE = 0.6


class ResultVerifier:
    """Verifies synthesis results against their source content.

    Checks that the synthesized answer is grounded in at least one source
    and meets the minimum confidence threshold.
    """

    def __init__(self, min_confidence: float = _MIN_VERIFIED_CONFIDENCE) -> None:
        """Initialize the result verifier.

        Args:
            min_confidence: Minimum confidence required to mark a result as verified.

        """
        self._min_confidence = min_confidence

    def _content_grounded(
        self,
        answer: str,
        sources: list[RetrievalResult],
    ) -> bool:
        """Check if the answer shares token overlap with any source.

        Args:
            answer: The synthesized answer string.
            sources: Source retrieval results to check against.

        Returns:
            True if any source shares at least one word with the answer.

        """
        answer_words = set(answer.lower().split())
        for source in sources:
            source_words = set(source.content.lower().split())
            if answer_words & source_words:
                return True
        return False

    def verify(self, synthesis: SynthesisResult) -> ValidationResult:
        """Verify a synthesis result for grounding and confidence.

        Args:
            synthesis: SynthesisResult to verify.

        Returns:
            ValidationResult indicating whether the synthesis is verified.

        """
        if not synthesis.answer.strip():
            return ValidationResult(
                valid=False,
                message="Empty answer cannot be verified",
            )
        if synthesis.confidence < self._min_confidence:
            return ValidationResult(
                valid=False,
                message=(
                    f"Confidence {synthesis.confidence:.2f} below threshold "
                    f"{self._min_confidence:.2f}"
                ),
            )
        if not self._content_grounded(synthesis.answer, synthesis.sources):
            return ValidationResult(
                valid=False,
                message="Answer not grounded in any source content",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"Verified: confidence={synthesis.confidence:.2f}, "
                f"sources={len(synthesis.sources)}"
            ),
        )

    def verify_and_mark(self, synthesis: SynthesisResult) -> SynthesisResult:
        """Verify a synthesis result and update its verified flag in place.

        Args:
            synthesis: SynthesisResult to verify and annotate.

        Returns:
            The input SynthesisResult with verified flag updated.

        """
        result = self.verify(synthesis)
        synthesis.verified = result.valid
        if result.valid:
            logger.info("Verification passed: %s", result.message)
        else:
            logger.info("Verification failed: %s", result.message)
        return synthesis


__all__ = ["ResultVerifier"]
