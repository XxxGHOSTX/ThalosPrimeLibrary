"""Tests for the BatchProcessor deterministic worker module.

Covers lifecycle methods (initialize, validate, operate, reconcile,
checkpoint, terminate), enqueue/process_batch/get_results operations,
error handling for individual items, and pending_count.
"""

import pytest

from thalos_prime.lob_babel_generator import BabelGenerator
from thalos_prime.lob_decoder import BabelDecoder
from thalos_prime.workers.batch_processor import BatchProcessor


def test_initialize_sets_up_state() -> None:
    """initialize() sets up the queue and results list."""
    proc = BatchProcessor(seed=42, batch_size=10)
    proc.initialize()

    assert proc.pending_count() == 0
    assert proc.get_results() == []
    proc.terminate()


def test_validate_before_initialize_raises() -> None:
    """validate() raises RuntimeError if called before initialize()."""
    proc = BatchProcessor(seed=42, batch_size=10)
    with pytest.raises(RuntimeError):
        proc.validate()


def test_validate_after_initialize_passes() -> None:
    """validate() succeeds after initialize()."""
    proc = BatchProcessor(seed=42, batch_size=10)
    proc.initialize()
    proc.validate()  # Should not raise
    proc.terminate()


def test_invalid_seed_raises_on_initialize() -> None:
    """initialize() raises ValueError for seed < 0."""
    proc = BatchProcessor(seed=-1, batch_size=10)
    with pytest.raises(ValueError):
        proc.initialize()


def test_invalid_batch_size_raises_on_initialize() -> None:
    """initialize() raises ValueError for batch_size <= 0."""
    proc = BatchProcessor(seed=0, batch_size=0)
    with pytest.raises(ValueError):
        proc.initialize()


def test_enqueue_returns_queue_size() -> None:
    """enqueue() adds items and returns the new queue length."""
    proc = BatchProcessor(seed=0, batch_size=50)
    proc.initialize()

    size = proc.enqueue([{"address": "abc"}, {"address": "def"}])

    assert size == 2
    assert proc.pending_count() == 2
    proc.terminate()


def test_process_batch_generates_and_scores() -> None:
    """process_batch() generates pages and returns scored results."""
    generator = BabelGenerator()
    decoder = BabelDecoder()
    proc = BatchProcessor(seed=0, batch_size=5)
    proc.initialize()

    proc.enqueue([{"address": "abc123"}, {"address": "def456"}])
    results = proc.process_batch(generator, decoder, query="hello")

    assert len(results) == 2
    for r in results:
        assert "address" in r
        assert "score" in r
        assert "confidence_level" in r
        assert "snippet" in r
        assert r["success"] is True
    proc.terminate()


def test_process_batch_sorted_by_score_desc() -> None:
    """process_batch() returns results sorted by score descending."""
    generator = BabelGenerator()
    decoder = BabelDecoder()
    proc = BatchProcessor(seed=0, batch_size=10)
    proc.initialize()

    # Enqueue several addresses
    addresses = [{"address": f"addr{i:04x}"} for i in range(5)]
    proc.enqueue(addresses)
    results = proc.process_batch(generator, decoder)

    scores = [float(r["score"]) for r in results]
    assert scores == sorted(scores, reverse=True)
    proc.terminate()


def test_process_batch_respects_batch_size() -> None:
    """process_batch() processes at most batch_size items per call."""
    generator = BabelGenerator()
    decoder = BabelDecoder()
    proc = BatchProcessor(seed=0, batch_size=2)
    proc.initialize()

    proc.enqueue([{"address": f"a{i}"} for i in range(5)])
    batch1 = proc.process_batch(generator, decoder)

    assert len(batch1) == 2
    assert proc.pending_count() == 3
    proc.terminate()


def test_get_results_accumulates_across_batches() -> None:
    """get_results() returns all accumulated results across multiple batches."""
    generator = BabelGenerator()
    decoder = BabelDecoder()
    proc = BatchProcessor(seed=0, batch_size=2)
    proc.initialize()

    proc.enqueue([{"address": f"x{i}"} for i in range(4)])
    proc.process_batch(generator, decoder)
    proc.process_batch(generator, decoder)

    all_results = proc.get_results()
    assert len(all_results) == 4
    proc.terminate()


def test_operate_is_noop() -> None:
    """operate() is a no-op and does not raise."""
    proc = BatchProcessor(seed=0, batch_size=10)
    proc.initialize()
    proc.operate()  # Should not raise
    proc.terminate()


def test_reconcile_is_noop_with_no_pending() -> None:
    """reconcile() completes without error when queue is empty."""
    proc = BatchProcessor(seed=0, batch_size=10)
    proc.initialize()
    proc.reconcile()  # Should not raise
    proc.terminate()


def test_checkpoint_returns_state_dict() -> None:
    """checkpoint() returns a dict with processing state."""
    generator = BabelGenerator()
    decoder = BabelDecoder()
    proc = BatchProcessor(seed=7, batch_size=5)
    proc.initialize()

    proc.enqueue([{"address": "chk1"}, {"address": "chk2"}])
    proc.process_batch(generator, decoder)

    state = proc.checkpoint()

    assert state["component"] == "BatchProcessor"
    assert state["seed"] == 7
    assert state["batch_size"] == 5
    assert state["processed_count"] == 2
    assert state["pending_count"] == 0
    assert state["last_batch_size"] == 2
    proc.terminate()


def test_terminate_clears_queue_and_results() -> None:
    """terminate() clears queue and results."""
    generator = BabelGenerator()
    decoder = BabelDecoder()
    proc = BatchProcessor(seed=0, batch_size=10)
    proc.initialize()
    proc.enqueue([{"address": "t1"}])
    proc.process_batch(generator, decoder)
    proc.terminate()

    # After terminate, validate should raise
    with pytest.raises(RuntimeError):
        proc.validate()


def test_enqueue_before_initialize_raises() -> None:
    """enqueue() raises RuntimeError if called before initialize()."""
    proc = BatchProcessor(seed=0, batch_size=10)
    with pytest.raises(RuntimeError):
        proc.enqueue([{"address": "x"}])


def test_pending_count_decreases_after_processing() -> None:
    """pending_count() decreases as items are processed."""
    generator = BabelGenerator()
    decoder = BabelDecoder()
    proc = BatchProcessor(seed=0, batch_size=3)
    proc.initialize()

    proc.enqueue([{"address": f"p{i}"} for i in range(6)])
    assert proc.pending_count() == 6

    proc.process_batch(generator, decoder)
    assert proc.pending_count() == 3
    proc.terminate()
