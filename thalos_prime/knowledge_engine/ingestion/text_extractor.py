"""Text extraction for the Knowledge Engine.

Extracts plain text from SourceRecord instances using BeautifulSoup4 for
HTML content and direct text for plain content.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from bs4 import BeautifulSoup

from thalos_prime.knowledge_engine.models import ArtifactRecord, SourceRecord, SourceType

logger = logging.getLogger(__name__)

_HTML_PARSER = "html.parser"
_METHOD_HTML = "beautifulsoup4"
_METHOD_TEXT = "plain"


class TextExtractor:
    """Lifecycle-managed text extractor.

    Uses BeautifulSoup4 for HTML sources and direct text pass-through
    for plain text sources.

    Example::

        extractor = TextExtractor()
        extractor.initialize()
        artifact = extractor.extract(source_record)
        extractor.terminate()

    """

    def __init__(self) -> None:
        """Initialize the text extractor."""
        self._initialized: bool = False
        self._extracted_count: int = 0

    def initialize(self) -> None:
        """Set up the text extractor."""
        self._extracted_count = 0
        self._initialized = True
        logger.info("TextExtractor initialized")

    def validate(self) -> None:
        """Verify that the extractor is properly initialized.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "TextExtractor.validate(): not initialized"
            raise RuntimeError(msg)
        logger.debug("TextExtractor validation passed")

    def operate(self) -> None:
        """No-op: work is performed via extract()."""
        logger.debug("TextExtractor.operate(): no-op — use extract()")

    def reconcile(self) -> None:
        """Log current extraction state.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "TextExtractor.reconcile(): not initialized"
            raise RuntimeError(msg)
        logger.info("TextExtractor.reconcile(): extracted_count=%d", self._extracted_count)

    def checkpoint(self) -> dict[str, object]:
        """Serialize current extractor state.

        Returns:
            Dictionary with component name and extracted count.

        """
        return {
            "component": "TextExtractor",
            "initialized": self._initialized,
            "extracted_count": self._extracted_count,
        }

    def terminate(self) -> None:
        """Shut down the text extractor."""
        self._initialized = False
        logger.info("TextExtractor terminated: extracted_count=%d", self._extracted_count)

    def extract(self, source: SourceRecord) -> ArtifactRecord:
        """Extract plain text from a source record.

        For URL sources, uses BeautifulSoup4 to strip HTML tags.
        For TEXT sources, returns content as-is.

        Args:
            source: The source record to extract text from.

        Returns:
            An ArtifactRecord with extracted plain text.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "TextExtractor.extract(): not initialized"
            raise RuntimeError(msg)
        if source.source_type == SourceType.URL:
            soup = BeautifulSoup(source.text_content, _HTML_PARSER)
            extracted = soup.get_text(separator=" ", strip=True)
            method = _METHOD_HTML
        else:
            extracted = source.text_content
            method = _METHOD_TEXT
        artifact = ArtifactRecord(
            id=str(uuid.uuid4()),
            source_id=source.id,
            extracted_text=extracted,
            extraction_method=method,
            created_at=datetime.now(UTC),
        )
        self._extracted_count += 1
        logger.info(
            "TextExtractor.extract(): source_id=%s method=%s len=%d",
            source.id,
            method,
            len(extracted),
        )
        return artifact
