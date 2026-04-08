"""Source ingestion for the Knowledge Engine.

Ingests content from URLs or raw text and produces SourceRecord instances
with deterministic content hashing.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime

import requests

from thalos_prime.knowledge_engine.models import SourceRecord, SourceType

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 30


class IngestionManager:
    """Lifecycle-managed source ingestion manager.

    Accepts URLs or plain text and produces SourceRecord instances with
    deterministic SHA-256 content hashes.

    Example::

        manager = IngestionManager()
        manager.initialize()
        record = manager.ingest_text("Hello world")
        manager.terminate()

    """

    def __init__(self) -> None:
        """Initialize the ingestion manager."""
        self._initialized: bool = False
        self._ingested_count: int = 0

    def initialize(self) -> None:
        """Set up the ingestion manager."""
        self._ingested_count = 0
        self._initialized = True
        logger.info("IngestionManager initialized")

    def validate(self) -> None:
        """Verify that the manager is properly initialized.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "IngestionManager.validate(): not initialized"
            raise RuntimeError(msg)
        logger.debug("IngestionManager validation passed: ingested_count=%d", self._ingested_count)

    def operate(self) -> None:
        """No-op: work is performed via ingest_url() and ingest_text()."""
        logger.debug("IngestionManager.operate(): no-op")

    def reconcile(self) -> None:
        """Log current ingestion state for reconciliation.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "IngestionManager.reconcile(): not initialized"
            raise RuntimeError(msg)
        logger.info("IngestionManager.reconcile(): ingested_count=%d", self._ingested_count)

    def checkpoint(self) -> dict[str, object]:
        """Serialize current ingestion state.

        Returns:
            Dictionary with component name and ingested count.

        """
        return {
            "component": "IngestionManager",
            "initialized": self._initialized,
            "ingested_count": self._ingested_count,
        }

    def terminate(self) -> None:
        """Shut down the ingestion manager."""
        self._initialized = False
        logger.info("IngestionManager terminated: ingested_count=%d", self._ingested_count)

    def ingest_url(self, url: str) -> SourceRecord:
        """Fetch content from a URL and produce a SourceRecord.

        Args:
            url: The URL to fetch content from.

        Returns:
            A SourceRecord with the fetched content.

        Raises:
            RuntimeError: If not initialized.
            requests.RequestException: If the HTTP request fails.

        """
        if not self._initialized:
            msg = "IngestionManager.ingest_url(): not initialized"
            raise RuntimeError(msg)
        response = requests.get(url, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        text_content = response.text
        content_hash = hashlib.sha256(text_content.encode("utf-8")).hexdigest()
        record = SourceRecord(
            id=str(uuid.uuid4()),
            url=url,
            text_content=text_content,
            source_type=SourceType.URL,
            content_hash=content_hash,
            created_at=datetime.now(UTC),
        )
        self._ingested_count += 1
        logger.info("IngestionManager.ingest_url(): url=%s hash=%s", url, content_hash)
        return record

    def ingest_text(
        self,
        text: str,
        metadata: dict[str, str] | None = None,
    ) -> SourceRecord:
        """Ingest plain text and produce a SourceRecord.

        Args:
            text: The text content to ingest.
            metadata: Optional metadata key-value pairs.

        Returns:
            A SourceRecord with the provided text.

        Raises:
            RuntimeError: If not initialized.
            ValueError: If text is empty.

        """
        if not self._initialized:
            msg = "IngestionManager.ingest_text(): not initialized"
            raise RuntimeError(msg)
        if not text.strip():
            msg = "IngestionManager.ingest_text(): text must not be empty"
            raise ValueError(msg)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        record = SourceRecord(
            id=str(uuid.uuid4()),
            url=None,
            text_content=text,
            source_type=SourceType.TEXT,
            content_hash=content_hash,
            created_at=datetime.now(UTC),
            metadata=metadata or {},
        )
        self._ingested_count += 1
        logger.info("IngestionManager.ingest_text(): hash=%s len=%d", content_hash, len(text))
        return record
