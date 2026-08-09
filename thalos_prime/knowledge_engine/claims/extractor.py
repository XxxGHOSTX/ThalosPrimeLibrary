"""Claim extraction for the Knowledge Engine.

Extracts factual claims from artifact text using sentence splitting.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime

from thalos_prime.knowledge_engine.models import ArtifactRecord, ClaimRecord, VerificationStatusEnum

logger = logging.getLogger(__name__)

_SENTENCE_SPLIT_PATTERN = re.compile(r"[.!?]+\s+")
_MIN_CLAIM_LEN = 10
_MAX_CLAIM_LEN = 500


class ClaimExtractor:
    """Lifecycle-managed claim extractor.

    Splits artifact text into sentences using punctuation boundaries and
    filters by length constraints.

    Example::

        extractor = ClaimExtractor()
        extractor.initialize()
        claims = extractor.extract_claims(artifact)
        extractor.terminate()

    """

    def __init__(self) -> None:
        """Initialize the claim extractor."""
        self._initialized: bool = False
        self._extracted_count: int = 0

    def initialize(self) -> None:
        """Set up the claim extractor."""
        self._extracted_count = 0
        self._initialized = True
        logger.info("ClaimExtractor initialized")

    def validate(self) -> None:
        """Verify that the extractor is properly initialized.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "ClaimExtractor.validate(): not initialized"
            raise RuntimeError(msg)
        logger.debug("ClaimExtractor validation passed")

    def operate(self) -> None:
        """No-op: work is performed via extract_claims()."""
        logger.debug("ClaimExtractor.operate(): no-op — use extract_claims()")

    def reconcile(self) -> None:
        """Log current extraction state.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "ClaimExtractor.reconcile(): not initialized"
            raise RuntimeError(msg)
        logger.info("ClaimExtractor.reconcile(): extracted_count=%d", self._extracted_count)

    def checkpoint(self) -> dict[str, object]:
        """Serialize current extractor state.

        Returns:
            Dictionary with component name and extracted count.

        """
        return {
            "component": "ClaimExtractor",
            "initialized": self._initialized,
            "extracted_count": self._extracted_count,
        }

    def terminate(self) -> None:
        """Shut down the claim extractor."""
        self._initialized = False
        logger.info("ClaimExtractor terminated: extracted_count=%d", self._extracted_count)

    def extract_claims(self, artifact: ArtifactRecord) -> list[ClaimRecord]:
        """Extract claims from an artifact.

        Args:
            artifact: The artifact to extract claims from.

        Returns:
            List of ClaimRecord instances.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "ClaimExtractor.extract_claims(): not initialized"
            raise RuntimeError(msg)
        sentences = _SENTENCE_SPLIT_PATTERN.split(artifact.extracted_text)
        claims: list[ClaimRecord] = []
        now = datetime.now(UTC)
        for raw_sentence in sentences:
            sentence = raw_sentence.strip()
            if not (_MIN_CLAIM_LEN <= len(sentence) <= _MAX_CLAIM_LEN):
                continue
            if sentence.startswith("http"):
                continue
            claim = ClaimRecord(
                id=str(uuid.uuid4()),
                artifact_id=artifact.id,
                text=sentence,
                score=0.0,
                status=VerificationStatusEnum.PENDING,
                created_at=now,
            )
            claims.append(claim)
        self._extracted_count += len(claims)
        logger.info(
            "ClaimExtractor.extract_claims(): artifact_id=%s claims=%d",
            artifact.id,
            len(claims),
        )
        return claims
