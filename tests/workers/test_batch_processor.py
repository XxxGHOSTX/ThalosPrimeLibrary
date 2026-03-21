"""Deterministic tests for BatchProcessor validation, guard, and error paths."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from thalos_prime.workers.batch_processor import BatchProcessor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_generator(page_text: str = "hello world") -> MagicMock:
    """Return a mock BabelGenerator that returns *page_text* from address_to_page."""
    gen = MagicMock()
    gen.address_to_page.return_value = page_text
    return gen


def _make_decoder(overall_score: float = 0.5) -> MagicMock:
    """Return a mock BabelDecoder whose score_coherence result has the given score."""
    coherence = MagicMock()
    coherence.overall_score = overall_score
    coherence.confidence_level = "moderate"
    dec = MagicMock()
    dec.score_coherence.return_value = coherence
    return dec


# ---------------------------------------------------------------------------
# Validation failure tests
# ---------------------------------------------------------------------------


class TestValidationFailures:
    """Tests that initialize() and validate() raise on invalid configuration."""

    def test_invalid_seed_raises_value_error(self) -> None:
        """initialize() must raise ValueError when seed < 0."""
        processor = BatchProcessor(seed=-1, batch_size=10)
        with pytest.raises(ValueError, match="seed must be >= 0"):
            processor.initialize()

    def test_invalid_batch_size_zero_raises_value_error(self) -> None:
        """initialize() must raise ValueError when batch_size == 0."""
        processor = BatchProcessor(seed=42, batch_size=0)
        with pytest.raises(ValueError, match="batch_size must be > 0"):
            processor.initialize()

    def test_invalid_batch_size_negative_raises_value_error(self) -> None:
        """initialize() must raise ValueError when batch_size < 0."""
        processor = BatchProcessor(seed=42, batch_size=-5)
        with pytest.raises(ValueError, match="batch_size must be > 0"):
            processor.initialize()

    def test_validate_negative_seed_when_initialized(self) -> None:
        """validate() must raise ValueError for seed < 0 when _initialized is True.

        Lines 102-104 of validate() are only reachable when _initialized is True
        but the seed is invalid; force that state directly to exercise the branch.
        """
        processor = BatchProcessor(seed=-1, batch_size=10)
        processor._initialized = True
        with pytest.raises(ValueError, match="seed must be >= 0"):
            processor.validate()

    def test_validate_zero_batch_size_when_initialized(self) -> None:
        """validate() must raise ValueError for batch_size == 0 when _initialized is True.

        Lines 105-107 of validate() are only reachable when _initialized is True
        but batch_size is invalid; force that state directly to exercise the branch.
        """
        processor = BatchProcessor(seed=42, batch_size=0)
        processor._initialized = True
        with pytest.raises(ValueError, match="batch_size must be > 0"):
            processor.validate()


# ---------------------------------------------------------------------------
# Initialization guard tests
# ---------------------------------------------------------------------------


class TestInitializationGuard:
    """Tests that un-initialized processors reject operations with RuntimeError."""

    def test_process_batch_before_initialize_raises(self) -> None:
        """process_batch() before initialize() must raise RuntimeError."""
        processor = BatchProcessor(seed=0, batch_size=10)
        gen = _make_generator()
        dec = _make_decoder()
        with pytest.raises(RuntimeError, match="not initialized"):
            processor.process_batch(gen, dec)

    def test_enqueue_before_initialize_raises(self) -> None:
        """enqueue() before initialize() must raise RuntimeError."""
        processor = BatchProcessor(seed=0, batch_size=10)
        with pytest.raises(RuntimeError, match="not initialized"):
            processor.enqueue([{"address": "abc"}])

    def test_validate_before_initialize_raises(self) -> None:
        """validate() before initialize() must raise RuntimeError."""
        processor = BatchProcessor(seed=0, batch_size=10)
        with pytest.raises(RuntimeError, match="not initialized"):
            processor.validate()


# ---------------------------------------------------------------------------
# Error handling path tests
# ---------------------------------------------------------------------------


class TestErrorHandlingPaths:
    """Tests that process_batch() captures per-item errors without propagating."""

    def test_generator_address_to_page_raises_runtime_error(self) -> None:
        """A RuntimeError from generator.address_to_page() produces a failure result."""
        processor = BatchProcessor(seed=1, batch_size=5)
        processor.initialize()
        processor.enqueue([{"address": "deadbeef"}])

        gen = MagicMock()
        gen.address_to_page.side_effect = RuntimeError("generator exploded")
        dec = _make_decoder()

        results = processor.process_batch(gen, dec, query="test")

        assert len(results) == 1
        result = results[0]
        assert result["success"] is False
        assert result["score"] == 0.0
        assert result["address"] == "deadbeef"
        assert "generator exploded" in result["error"]

    def test_decoder_score_coherence_raises_runtime_error(self) -> None:
        """A RuntimeError from decoder.score_coherence() produces a failure result."""
        processor = BatchProcessor(seed=2, batch_size=5)
        processor.initialize()
        processor.enqueue([{"address": "cafebabe"}])

        gen = _make_generator("some page text")
        dec = MagicMock()
        dec.score_coherence.side_effect = RuntimeError("decoder exploded")

        results = processor.process_batch(gen, dec, query="query")

        assert len(results) == 1
        result = results[0]
        assert result["success"] is False
        assert result["score"] == 0.0
        assert result["address"] == "cafebabe"
        assert "decoder exploded" in result["error"]

    def test_failed_items_do_not_block_subsequent_items(self) -> None:
        """A failure on one item must not stop other items from being processed."""
        processor = BatchProcessor(seed=3, batch_size=10)
        processor.initialize()
        processor.enqueue([{"address": "fail"}, {"address": "ok"}])

        gen = MagicMock()
        gen.address_to_page.side_effect = [
            RuntimeError("first fails"),
            "good page text",
        ]
        dec = _make_decoder(overall_score=0.9)

        results = processor.process_batch(gen, dec)

        assert len(results) == 2
        success_results = [r for r in results if r["success"] is True]
        failure_results = [r for r in results if r["success"] is False]
        assert len(success_results) == 1
        assert len(failure_results) == 1

    def test_processed_count_incremented_on_failure(self) -> None:
        """processed_count must increment even when an item fails."""
        processor = BatchProcessor(seed=4, batch_size=5)
        processor.initialize()
        processor.enqueue([{"address": "x"}, {"address": "y"}])

        gen = MagicMock()
        gen.address_to_page.side_effect = RuntimeError("boom")
        dec = _make_decoder()

        processor.process_batch(gen, dec)

        cp: dict[str, Any] = processor.checkpoint()
        assert cp["processed_count"] == 2
