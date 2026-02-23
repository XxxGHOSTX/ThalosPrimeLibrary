"""Tests for the SQLite-backed ResultStore persistence module.

Covers lifecycle methods (initialize, validate, operate, reconcile,
checkpoint, terminate), search result CRUD, session management,
and expired session cleanup.
"""

import time

import pytest

from thalos_prime.database.store import ResultStore


def test_initialize_creates_tables() -> None:
    """initialize() creates search_results and sessions tables."""
    store = ResultStore(db_path=":memory:")
    store.initialize()
    store.validate()  # Should not raise if tables exist
    store.terminate()


def test_validate_before_initialize_raises() -> None:
    """validate() raises RuntimeError if called before initialize()."""
    store = ResultStore(db_path=":memory:")
    with pytest.raises(RuntimeError):
        store.validate()


def test_validate_after_initialize_passes() -> None:
    """validate() succeeds after a successful initialize()."""
    store = ResultStore(db_path=":memory:")
    store.initialize()
    store.validate()  # Should not raise
    store.terminate()


def test_save_and_get_results() -> None:
    """save_result() inserts a record; get_results() retrieves it."""
    store = ResultStore(db_path=":memory:")
    store.initialize()

    rowid = store.save_result(
        query="hello",
        address="abc123",
        score=75,
        snippet="hello world snippet",
        timestamp=time.time(),
    )

    assert rowid > 0

    results = store.get_results("hello")
    assert len(results) == 1
    assert results[0]["address"] == "abc123"
    assert results[0]["score"] == 75
    store.terminate()


def test_get_results_empty_for_missing_query() -> None:
    """get_results() returns an empty list when no results exist for a query."""
    store = ResultStore(db_path=":memory:")
    store.initialize()

    results = store.get_results("nonexistent query")
    assert results == []
    store.terminate()


def test_get_results_sorted_by_score_desc() -> None:
    """get_results() returns results ordered by score descending."""
    store = ResultStore(db_path=":memory:")
    store.initialize()

    ts = time.time()
    store.save_result("q", "addr1", 30, "low", ts)
    store.save_result("q", "addr2", 90, "high", ts)
    store.save_result("q", "addr3", 60, "mid", ts)

    results = store.get_results("q")
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    store.terminate()


def test_get_results_respects_limit() -> None:
    """get_results() honours the limit parameter."""
    store = ResultStore(db_path=":memory:")
    store.initialize()

    ts = time.time()
    for i in range(10):
        store.save_result("q", f"addr{i}", i * 10, f"snip{i}", ts)

    results = store.get_results("q", limit=3)
    assert len(results) == 3
    store.terminate()


def test_save_and_get_session() -> None:
    """save_session() stores data; get_session() retrieves it."""
    store = ResultStore(db_path=":memory:")
    store.initialize()

    store.save_session("sess-001", '{"user": "alice"}')
    data = store.get_session("sess-001")

    assert data == '{"user": "alice"}'
    store.terminate()


def test_get_session_missing_returns_none() -> None:
    """get_session() returns None for an unknown session ID."""
    store = ResultStore(db_path=":memory:")
    store.initialize()

    assert store.get_session("does-not-exist") is None
    store.terminate()


def test_save_session_upsert() -> None:
    """save_session() updates existing session data on conflict."""
    store = ResultStore(db_path=":memory:")
    store.initialize()

    store.save_session("sess-002", "initial")
    store.save_session("sess-002", "updated")

    assert store.get_session("sess-002") == "updated"
    store.terminate()


def test_delete_expired_sessions() -> None:
    """delete_expired_sessions() removes sessions older than max_age_seconds."""
    store = ResultStore(db_path=":memory:")
    store.initialize()

    store.save_session("old-sess", "old data")
    # Force the updated_at to be in the past by deleting and re-inserting
    # with a very small max_age so it expires immediately
    time.sleep(0.05)
    deleted = store.delete_expired_sessions(max_age_seconds=0)

    assert deleted >= 1
    assert store.get_session("old-sess") is None
    store.terminate()


def test_operate_is_noop() -> None:
    """operate() is a no-op and does not raise."""
    store = ResultStore(db_path=":memory:")
    store.initialize()
    store.operate()  # Should not raise
    store.terminate()


def test_reconcile_integrity_check_passes() -> None:
    """reconcile() runs PRAGMA integrity_check without error on a valid DB."""
    store = ResultStore(db_path=":memory:")
    store.initialize()
    store.reconcile()  # Should not raise
    store.terminate()


def test_checkpoint_returns_row_counts() -> None:
    """checkpoint() returns a dict with row counts for all managed tables."""
    store = ResultStore(db_path=":memory:")
    store.initialize()

    store.save_result("q", "addr1", 80, "snip", time.time())
    store.save_session("s1", "data")

    state = store.checkpoint()

    assert state["component"] == "ResultStore"
    assert state["search_results_count"] == 1
    assert state["sessions_count"] == 1
    store.terminate()


def test_terminate_closes_connection() -> None:
    """terminate() closes the connection; subsequent operations raise RuntimeError."""
    store = ResultStore(db_path=":memory:")
    store.initialize()
    store.terminate()

    with pytest.raises(RuntimeError):
        store.get_results("q")


def test_save_result_before_initialize_raises() -> None:
    """save_result() raises RuntimeError if called before initialize()."""
    store = ResultStore(db_path=":memory:")
    with pytest.raises(RuntimeError):
        store.save_result("q", "addr", 0, "snip", 0.0)
