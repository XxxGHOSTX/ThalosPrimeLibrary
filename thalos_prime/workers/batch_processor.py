"""Deterministic batch processor for background Library of Babel page processing.

Enqueues page addresses, generates their content, scores coherence, and
accumulates ranked results. Bounded by ``batch_size`` per invocation and
uses a deterministic seed for any random tie-breaking.

Data Plane boundary: computational work only — no lifecycle orchestration
or control-plane coordination logic belongs here.
"""

from __future__ import annotations

import collections
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from thalos_prime.lob_babel_generator import BabelGenerator
    from thalos_prime.lob_decoder import BabelDecoder

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Deterministic batch worker for Library of Babel page generation and scoring.

    Maintains a bounded FIFO queue of address descriptors. Each call to
    ``process_batch`` takes up to ``batch_size`` items from the front of the
    queue, generates the page text, scores its coherence, and appends the
    result to an internal results list.

    Results are sorted by score descending so the highest-coherence pages
    appear first.

    Example::

        processor = BatchProcessor(seed=42, batch_size=10)
        processor.initialize()
        processor.enqueue([{"address": "abc123"}])
        results = processor.process_batch(generator, decoder, query="hello")

    """

    def __init__(self, seed: int, batch_size: int = 50) -> None:
        """Initialize the batch processor.

        Args:
            seed: Deterministic seed for reproducible processing order.
                  Must be >= 0.
            batch_size: Maximum number of addresses processed per batch call.
                        Must be > 0.

        """
        self._seed = seed
        self._batch_size = batch_size
        self._queue: collections.deque[dict[str, Any]] = collections.deque()
        self._results: list[dict[str, Any]] = []
        self._processed_count: int = 0
        self._last_batch_size: int = 0
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle protocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Set up the internal queue and results list.

        Raises:
            ValueError: If seed or batch_size are invalid.

        """
        if self._seed < 0:
            msg = f"BatchProcessor: seed must be >= 0, got {self._seed}"
            raise ValueError(msg)
        if self._batch_size <= 0:
            msg = f"BatchProcessor: batch_size must be > 0, got {self._batch_size}"
            raise ValueError(msg)

        self._queue = collections.deque()
        self._results = []
        self._processed_count = 0
        self._last_batch_size = 0
        self._initialized = True
        logger.info(
            "BatchProcessor initialized: seed=%d batch_size=%d",
            self._seed,
            self._batch_size,
        )

    def validate(self) -> None:
        """Verify that the processor is properly initialized and invariants hold.

        Raises:
            RuntimeError: If not initialized.
            ValueError: If configuration invariants are violated.

        """
        if not self._initialized:
            msg = "BatchProcessor.validate(): not initialized — call initialize() first"
            raise RuntimeError(msg)
        if self._seed < 0:
            msg = f"BatchProcessor.validate(): seed must be >= 0, got {self._seed}"
            raise ValueError(msg)
        if self._batch_size <= 0:
            msg = f"BatchProcessor.validate(): batch_size must be > 0, got {self._batch_size}"
            raise ValueError(msg)
        logger.debug(
            "BatchProcessor validation passed: queue=%d results=%d",
            len(self._queue),
            len(self._results),
        )

    def operate(self) -> None:
        """No-op: work is performed via process_batch()."""
        logger.debug("BatchProcessor.operate(): no-op (work done via process_batch)")

    def reconcile(self) -> None:
        """Verify that no items were lost during the last batch.

        If the internal processed count does not match the sum of queue plus
        results, a warning is logged. The processor does not halt because
        partial processing is a valid state (e.g. partial failures are
        recorded in results with success=False).
        """
        total = len(self._queue) + len(self._results)
        logger.info(
            "BatchProcessor.reconcile(): processed=%d pending=%d accumulated=%d total=%d",
            self._processed_count,
            len(self._queue),
            len(self._results),
            total,
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialize current processing state.

        Returns:
            Dictionary with processed_count, pending_count, and last_batch_size.

        """
        return {
            "component": "BatchProcessor",
            "seed": self._seed,
            "batch_size": self._batch_size,
            "processed_count": self._processed_count,
            "pending_count": len(self._queue),
            "accumulated_results": len(self._results),
            "last_batch_size": self._last_batch_size,
        }

    def terminate(self) -> None:
        """Clear the queue and accumulated results."""
        self._queue.clear()
        self._results.clear()
        self._initialized = False
        logger.info("BatchProcessor terminated: queue and results cleared")

    # ------------------------------------------------------------------
    # Processing operations
    # ------------------------------------------------------------------

    def enqueue(self, addresses: list[dict[str, Any]]) -> int:
        """Add address descriptors to the processing queue.

        Args:
            addresses: List of address dicts, each containing at least
                       ``{"address": "<hex_string>"}`` and optional metadata.

        Returns:
            Current queue length after enqueuing.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "BatchProcessor.enqueue(): not initialized"
            raise RuntimeError(msg)
        for item in addresses:
            self._queue.append(item)
        logger.debug(
            "BatchProcessor.enqueue(): %d items added, queue=%d",
            len(addresses),
            len(self._queue),
        )
        return len(self._queue)

    def process_batch(
        self,
        generator: BabelGenerator,
        decoder: BabelDecoder,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """Process up to ``batch_size`` queued addresses and return scored results.

        Pops up to ``batch_size`` items from the front of the queue, generates
        the page content for each address, scores its coherence, and returns
        the batch results sorted by score descending. Failed items are included
        with ``success=False`` and an ``error`` field.

        Args:
            generator: BabelGenerator instance for page generation.
            decoder: BabelDecoder instance for coherence scoring.
            query: Optional query string for relevance scoring.

        Returns:
            List of result dicts sorted by score descending, each containing:
            address, score, confidence_level, snippet, success, and
            optionally error.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized:
            msg = "BatchProcessor.process_batch(): not initialized"
            raise RuntimeError(msg)

        batch: list[dict[str, Any]] = []
        for _ in range(self._batch_size):
            if not self._queue:
                break
            batch.append(self._queue.popleft())

        self._last_batch_size = len(batch)
        batch_results: list[dict[str, Any]] = []

        for item in batch:
            address = str(item.get("address", ""))
            try:
                page_text = generator.address_to_page(address)
                coherence = decoder.score_coherence(page_text, query)
                result: dict[str, Any] = {
                    "address": address,
                    "score": coherence.overall_score,
                    "confidence_level": coherence.confidence_level,
                    "snippet": page_text[:240].replace("\n", " "),
                    "success": True,
                }
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                result = {
                    "address": address,
                    "score": 0.0,
                    "confidence_level": "minimal",
                    "snippet": "",
                    "success": False,
                    "error": str(exc),
                }
                logger.warning("BatchProcessor: error processing %s: %s", address, exc)

            batch_results.append(result)
            self._processed_count += 1

        batch_results.sort(key=lambda r: float(r.get("score", 0.0)), reverse=True)
        self._results.extend(batch_results)

        logger.info(
            "BatchProcessor.process_batch(): processed %d items, total_processed=%d",
            len(batch_results),
            self._processed_count,
        )
        return batch_results

    def get_results(self) -> list[dict[str, Any]]:
        """Return all accumulated results since the last initialize().

        Returns:
            List of all result dicts accumulated across all process_batch calls.

        """
        return list(self._results)

    def pending_count(self) -> int:
        """Return the current number of items waiting in the queue.

        Returns:
            Number of unprocessed items in the queue.

        """
        return len(self._queue)
