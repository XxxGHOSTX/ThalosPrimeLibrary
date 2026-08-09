"""Verification scoring for the Knowledge Engine.

Provides multi-metric scoring for claims based on evidence support,
contradiction penalties, source trust, and translation stability.
"""

from __future__ import annotations

import logging

from thalos_prime.knowledge_engine.models import (
    ClaimRecord,
    ContradictionRecord,
    EvidenceSpan,
    SourceRecord,
    SourceType,
    VerificationStatusEnum,
)

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.8
_UNCERTAIN_THRESHOLD = 0.4


class VerificationScorer:
    """Lifecycle-managed verification scorer.

    Combines multiple scoring metrics into an overall claim score.

    Example::

        scorer = VerificationScorer()
        scorer.initialize()
        score = scorer.score_claim(claim, spans, contradictions, source, 1.0)
        scorer.terminate()

    """

    def __init__(self) -> None:
        """Initialize the verification scorer."""
        self._initialized: bool = False
        self._scored_count: int = 0

    def initialize(self) -> None:
        """Set up the verification scorer."""
        self._scored_count = 0
        self._initialized = True
        logger.info("VerificationScorer initialized")

    def validate(self) -> None:
        """Verify that the scorer is properly initialized.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "VerificationScorer.validate(): not initialized"
            raise RuntimeError(msg)
        logger.debug("VerificationScorer validation passed")

    def operate(self) -> None:
        """No-op: work is performed via score_claim()."""
        logger.debug("VerificationScorer.operate(): no-op — use score_claim()")

    def reconcile(self) -> None:
        """Log current scoring state.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "VerificationScorer.reconcile(): not initialized"
            raise RuntimeError(msg)
        logger.info("VerificationScorer.reconcile(): scored_count=%d", self._scored_count)

    def checkpoint(self) -> dict[str, object]:
        """Serialize current scorer state.

        Returns:
            Dictionary with component name and scored count.

        """
        return {
            "component": "VerificationScorer",
            "initialized": self._initialized,
            "scored_count": self._scored_count,
        }

    def terminate(self) -> None:
        """Shut down the verification scorer."""
        self._initialized = False
        logger.info("VerificationScorer terminated: scored_count=%d", self._scored_count)

    def score_translation_stability(self, text: str, stability_score: float) -> float:
        """Score based on translation stability.

        Args:
            text: The text being scored (unused but kept for interface symmetry).
            stability_score: Stability score from TranslationService (0.0-1.0).

        Returns:
            The stability score clamped to [0.0, 1.0].

        """
        _ = text
        return max(0.0, min(1.0, stability_score))

    def score_evidence_support(
        self,
        claim: ClaimRecord,
        evidence_spans: list[EvidenceSpan],
    ) -> float:
        """Score based on evidence support.

        Args:
            claim: The claim being scored.
            evidence_spans: Evidence spans found for this claim.

        Returns:
            Score in [0.0, 1.0]: 1.0 if evidence found, 0.0 otherwise.

        """
        _ = claim
        return 1.0 if evidence_spans else 0.0

    def score_contradiction_penalty(
        self,
        claim_id: str,
        contradictions: list[ContradictionRecord],
    ) -> float:
        """Compute contradiction penalty for a claim.

        Args:
            claim_id: The ID of the claim being scored.
            contradictions: Contradictions involving this claim.

        Returns:
            Penalty in [0.0, 1.0]: average contradiction score.

        """
        _ = claim_id
        if not contradictions:
            return 0.0
        avg = sum(c.contradiction_score for c in contradictions) / len(contradictions)
        return max(0.0, min(1.0, avg))

    def score_source_trust(self, source_record: SourceRecord) -> float:
        """Score based on source trust.

        URL sources get higher base trust (0.8) vs plain text (0.6).

        Args:
            source_record: The source record.

        Returns:
            Trust score in [0.0, 1.0].

        """
        if source_record.source_type == SourceType.URL:
            return 0.8
        return 0.6

    def score_claim(
        self,
        claim: ClaimRecord,
        evidence_spans: list[EvidenceSpan],
        contradictions: list[ContradictionRecord],
        source_record: SourceRecord,
        translation_stability: float,
    ) -> float:
        """Compute overall claim score from multiple metrics.

        Args:
            claim: The claim to score.
            evidence_spans: Evidence spans for this claim.
            contradictions: Contradictions involving this claim.
            source_record: The source for this claim.
            translation_stability: Stability score from TranslationService.

        Returns:
            Overall score in [0.0, 1.0].

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "VerificationScorer.score_claim(): not initialized"
            raise RuntimeError(msg)
        stability = self.score_translation_stability(claim.text, translation_stability)
        evidence = self.score_evidence_support(claim, evidence_spans)
        penalty = self.score_contradiction_penalty(claim.id, contradictions)
        trust = self.score_source_trust(source_record)
        score = (stability * 0.25 + evidence * 0.40 + trust * 0.35) - (penalty * 0.50)
        score = max(0.0, min(1.0, score))
        self._scored_count += 1
        logger.info(
            "VerificationScorer.score_claim(): claim_id=%s score=%.3f",
            claim.id,
            score,
        )
        return score

    def determine_status(self, score: float) -> VerificationStatusEnum:
        """Determine verification status from a score.

        Args:
            score: The overall score in [0.0, 1.0].

        Returns:
            VerificationStatusEnum based on score thresholds.

        """
        if score >= CONFIDENCE_THRESHOLD:
            return VerificationStatusEnum.VERIFIED
        if score >= _UNCERTAIN_THRESHOLD:
            return VerificationStatusEnum.UNCERTAIN
        return VerificationStatusEnum.REJECTED
