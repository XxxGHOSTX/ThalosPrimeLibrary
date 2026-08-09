"""Evidence linking for the Knowledge Engine.

Links claims to evidence spans within source content.
"""

from __future__ import annotations

import logging
import uuid

from thalos_prime.knowledge_engine.models import ClaimRecord, EvidenceSpan, SourceRecord

logger = logging.getLogger(__name__)


class EvidenceLinker:
    """Lifecycle-managed evidence linker.

    Finds occurrences of claim text within source text_content and
    produces EvidenceSpan records.

    Example::

        linker = EvidenceLinker()
        linker.initialize()
        spans = linker.link(claim, source)
        linker.terminate()

    """

    def __init__(self) -> None:
        """Initialize the evidence linker."""
        self._initialized: bool = False
        self._linked_count: int = 0

    def initialize(self) -> None:
        """Set up the evidence linker."""
        self._linked_count = 0
        self._initialized = True
        logger.info("EvidenceLinker initialized")

    def validate(self) -> None:
        """Verify that the linker is properly initialized.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "EvidenceLinker.validate(): not initialized"
            raise RuntimeError(msg)
        logger.debug("EvidenceLinker validation passed")

    def operate(self) -> None:
        """No-op: work is performed via link()."""
        logger.debug("EvidenceLinker.operate(): no-op — use link()")

    def reconcile(self) -> None:
        """Log current linking state.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "EvidenceLinker.reconcile(): not initialized"
            raise RuntimeError(msg)
        logger.info("EvidenceLinker.reconcile(): linked_count=%d", self._linked_count)

    def checkpoint(self) -> dict[str, object]:
        """Serialize current linker state.

        Returns:
            Dictionary with component name and linked count.

        """
        return {
            "component": "EvidenceLinker",
            "initialized": self._initialized,
            "linked_count": self._linked_count,
        }

    def terminate(self) -> None:
        """Shut down the evidence linker."""
        self._initialized = False
        logger.info("EvidenceLinker terminated: linked_count=%d", self._linked_count)

    def link(self, claim: ClaimRecord, source: SourceRecord) -> list[EvidenceSpan]:
        """Find evidence spans for a claim within a source.

        Args:
            claim: The claim to find evidence for.
            source: The source to search within.

        Returns:
            List of EvidenceSpan records for each occurrence found.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "EvidenceLinker.link(): not initialized"
            raise RuntimeError(msg)
        spans: list[EvidenceSpan] = []
        content = source.text_content
        claim_text = claim.text
        start = 0
        while True:
            idx = content.find(claim_text, start)
            if idx == -1:
                break
            span = EvidenceSpan(
                id=str(uuid.uuid4()),
                claim_id=claim.id,
                source_id=source.id,
                span_text=claim_text,
                start_offset=idx,
                end_offset=idx + len(claim_text),
            )
            spans.append(span)
            start = idx + 1
        self._linked_count += len(spans)
        logger.info(
            "EvidenceLinker.link(): claim_id=%s source_id=%s spans=%d",
            claim.id,
            source.id,
            len(spans),
        )
        return spans
