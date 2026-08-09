"""Translation stability service for the Knowledge Engine.

Provides heuristic-based translation stability scoring.
Full multi-language translation is outside scope.
"""

from __future__ import annotations

import logging

from thalos_prime.knowledge_engine.models import ArtifactRecord

logger = logging.getLogger(__name__)

_ASCII_THRESHOLD = 0.8


class TranslationService:
    """Lifecycle-managed translation stability service.

    Uses a heuristic: if more than 80% of characters are ASCII, treat as
    English with stability=1.0; otherwise stability=0.0.

    Example::

        service = TranslationService()
        service.initialize()
        artifact, stability = service.translate(artifact)
        service.terminate()

    """

    def __init__(self) -> None:
        """Initialize the translation service."""
        self._initialized: bool = False
        self._translated_count: int = 0

    def initialize(self) -> None:
        """Set up the translation service."""
        self._translated_count = 0
        self._initialized = True
        logger.info("TranslationService initialized")

    def validate(self) -> None:
        """Verify that the service is properly initialized.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "TranslationService.validate(): not initialized"
            raise RuntimeError(msg)
        logger.debug("TranslationService validation passed")

    def operate(self) -> None:
        """No-op: work is performed via translate()."""
        logger.debug("TranslationService.operate(): no-op — use translate()")

    def reconcile(self) -> None:
        """Log current translation state.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "TranslationService.reconcile(): not initialized"
            raise RuntimeError(msg)
        logger.info("TranslationService.reconcile(): translated_count=%d", self._translated_count)

    def checkpoint(self) -> dict[str, object]:
        """Serialize current service state.

        Returns:
            Dictionary with component name and translated count.

        """
        return {
            "component": "TranslationService",
            "initialized": self._initialized,
            "translated_count": self._translated_count,
        }

    def terminate(self) -> None:
        """Shut down the translation service."""
        self._initialized = False
        logger.info("TranslationService terminated: translated_count=%d", self._translated_count)

    def translate(self, artifact: ArtifactRecord) -> tuple[ArtifactRecord, float]:
        """Assess translation stability of an artifact.

        Heuristic: if more than 80% of characters are ASCII, treat as
        English with stability=1.0; otherwise stability=0.0.

        Args:
            artifact: The artifact to assess.

        Returns:
            Tuple of (artifact, stability_score).

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "TranslationService.translate(): not initialized"
            raise RuntimeError(msg)
        text = artifact.extracted_text
        if not text:
            self._translated_count += 1
            return artifact, 1.0
        ascii_count = sum(1 for ch in text if ord(ch) < 128)
        ratio = ascii_count / len(text)
        stability = 1.0 if ratio > _ASCII_THRESHOLD else 0.0
        self._translated_count += 1
        logger.info(
            "TranslationService.translate(): artifact_id=%s stability=%.2f",
            artifact.id,
            stability,
        )
        return artifact, stability
