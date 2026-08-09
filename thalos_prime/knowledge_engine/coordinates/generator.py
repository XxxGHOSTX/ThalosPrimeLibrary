"""Deterministic coordinate generation for the Knowledge Engine.

Generates Library of Babel coordinates from content and lineage hashes
using SHA-256 for full determinism.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from thalos_prime.knowledge_engine.models import CoordinateRecord

logger = logging.getLogger(__name__)


class CoordinateGenerator:
    """Lifecycle-managed coordinate generator.

    Produces deterministic CoordinateRecord instances from content hash,
    lineage hash, and semantic cluster using SHA-256.

    Example::

        gen = CoordinateGenerator()
        gen.initialize()
        coord = gen.generate("content", "lineage_hash", 0)
        gen.terminate()

    """

    def __init__(self) -> None:
        """Initialize the coordinate generator."""
        self._initialized: bool = False
        self._generated_count: int = 0

    def initialize(self) -> None:
        """Set up the coordinate generator."""
        self._generated_count = 0
        self._initialized = True
        logger.info("CoordinateGenerator initialized")

    def validate(self) -> None:
        """Verify that the generator is properly initialized.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "CoordinateGenerator.validate(): not initialized"
            raise RuntimeError(msg)
        logger.debug("CoordinateGenerator validation passed")

    def operate(self) -> None:
        """No-op: work is performed via generate()."""
        logger.debug("CoordinateGenerator.operate(): no-op — use generate()")

    def reconcile(self) -> None:
        """Log current generation state.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "CoordinateGenerator.reconcile(): not initialized"
            raise RuntimeError(msg)
        logger.info("CoordinateGenerator.reconcile(): generated_count=%d", self._generated_count)

    def checkpoint(self) -> dict[str, object]:
        """Serialize current generator state.

        Returns:
            Dictionary with component name and generated count.

        """
        return {
            "component": "CoordinateGenerator",
            "initialized": self._initialized,
            "generated_count": self._generated_count,
        }

    def terminate(self) -> None:
        """Shut down the coordinate generator."""
        self._initialized = False
        logger.info("CoordinateGenerator terminated: generated_count=%d", self._generated_count)

    def generate(
        self,
        content: str,
        lineage_hash: str,
        semantic_cluster: int,
    ) -> CoordinateRecord:
        """Generate a deterministic coordinate for content.

        Args:
            content: The content to generate a coordinate for.
            lineage_hash: The lineage hash for provenance tracking.
            semantic_cluster: The semantic cluster index.

        Returns:
            A CoordinateRecord with deterministic coordinate_hex.

        Raises:
            RuntimeError: If not initialized.
            ValueError: If semantic_cluster is negative.

        """
        if not self._initialized:
            msg = "CoordinateGenerator.generate(): not initialized"
            raise RuntimeError(msg)
        if semantic_cluster < 0:
            msg = (
                f"CoordinateGenerator.generate(): semantic_cluster must be >= 0, "
                f"got {semantic_cluster}"
            )
            raise ValueError(msg)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        combined = f"{content_hash}:{lineage_hash}:{semantic_cluster}"
        coordinate_hex = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        record = CoordinateRecord(
            id=str(uuid.uuid4()),
            content_hash=content_hash,
            lineage_hash=lineage_hash,
            semantic_cluster=semantic_cluster,
            coordinate_hex=coordinate_hex,
            created_at=datetime.now(UTC),
        )
        self._generated_count += 1
        logger.info(
            "CoordinateGenerator.generate(): coordinate_hex=%s cluster=%d",
            coordinate_hex[:16],
            semantic_cluster,
        )
        return record
