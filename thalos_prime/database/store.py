"""SQLite-based persistence layer for Thalos Prime search results and sessions.

Provides a lifecycle-managed ``ResultStore`` backed by Python's built-in
``sqlite3`` module. Stores search results and user sessions with full
integrity checking, ordered retrieval, and TTL-based session cleanup.

No external dependencies required — stdlib ``sqlite3`` only.

Data Plane boundary: persistence only — no lifecycle orchestration or
control-plane coordination logic belongs here.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any

logger = logging.getLogger(__name__)

_CREATE_SEARCH_RESULTS = """
CREATE TABLE IF NOT EXISTS search_results (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    query     TEXT    NOT NULL,
    address   TEXT    NOT NULL,
    score     INTEGER NOT NULL,
    snippet   TEXT    NOT NULL,
    timestamp REAL    NOT NULL
)
"""

_CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT    PRIMARY KEY,
    data       TEXT    NOT NULL,
    updated_at REAL    NOT NULL
)
"""


class ResultStore:
    """SQLite-backed store for search results and user sessions.

    Implements the full lifecycle protocol for deterministic initialization,
    validation, reconciliation, checkpointing, and teardown.

    Example::

        store = ResultStore(db_path=":memory:")
        store.initialize()
        store.validate()
        rowid = store.save_result("hello", "abc123", 90, "snippet…", 1700000000.0)
        results = store.get_results("hello")
        store.terminate()

    """

    def __init__(self, db_path: str = ":memory:") -> None:
        """Initialize the store with a database path.

        Args:
            db_path: Path to the SQLite database file, or ``:memory:``
                for an in-memory database.

        """
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle protocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Open the database connection and create tables if they do not exist.

        Raises:
            RuntimeError: If the connection cannot be established.
            sqlite3.Error: If table creation fails.

        """
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        cursor = self._conn.cursor()
        cursor.execute(_CREATE_SEARCH_RESULTS)
        cursor.execute(_CREATE_SESSIONS)
        self._conn.commit()
        self._initialized = True
        logger.info("ResultStore initialized: db_path=%s", self._db_path)

    def validate(self) -> None:
        """Verify that the connection is open and required tables exist.

        Raises:
            RuntimeError: If not initialized or the connection is closed.
            sqlite3.Error: If the integrity check or table query fails.

        """
        if not self._initialized or self._conn is None:
            msg = "ResultStore.validate(): not initialized — call initialize() first"
            raise RuntimeError(msg)
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN (?, ?)",
            ("search_results", "sessions"),
        )
        tables = {row["name"] for row in cursor.fetchall()}
        missing = {"search_results", "sessions"} - tables
        if missing:
            msg = f"ResultStore.validate(): expected tables missing: {missing}"
            raise RuntimeError(msg)
        logger.debug("ResultStore validation passed")

    def operate(self) -> None:
        """No-op: store is passive and serves requests on demand."""
        logger.debug("ResultStore.operate(): no-op (passive component)")

    def reconcile(self) -> None:
        """Run SQLite integrity check to verify database consistency.

        Raises:
            RuntimeError: If not initialized or integrity check fails.

        """
        if self._conn is None:
            msg = "ResultStore.reconcile(): not initialized"
            raise RuntimeError(msg)
        cursor = self._conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        rows = cursor.fetchall()
        result = rows[0][0] if rows else "unknown"
        if result != "ok":
            msg = f"ResultStore.reconcile(): integrity check failed: {result}"
            raise RuntimeError(msg)
        logger.info("ResultStore reconciliation complete: integrity=%s", result)

    def checkpoint(self) -> dict[str, object]:
        """Return row counts for all managed tables.

        Returns:
            Dictionary with row counts for search_results and sessions tables.

        Raises:
            RuntimeError: If not initialized.

        """
        if self._conn is None:
            msg = "ResultStore.checkpoint(): not initialized"
            raise RuntimeError(msg)
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM search_results")
        sr_count: int = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM sessions")
        sess_count: int = cursor.fetchone()[0]
        return {
            "component": "ResultStore",
            "db_path": self._db_path,
            "search_results_count": sr_count,
            "sessions_count": sess_count,
        }

    def terminate(self) -> None:
        """Commit pending writes and close the database connection."""
        if self._conn is not None:
            self._conn.commit()
            self._conn.close()
            self._conn = None
        self._initialized = False
        logger.info("ResultStore terminated: connection closed")

    # ------------------------------------------------------------------
    # Search result persistence
    # ------------------------------------------------------------------

    def save_result(
        self,
        query: str,
        address: str,
        score: int,
        snippet: str,
        timestamp: float,
    ) -> int:
        """Insert a search result and return the new row ID.

        Args:
            query: The search query string.
            address: The hexadecimal page address.
            score: Coherence score (0-100).
            snippet: Short text excerpt from the page.
            timestamp: Unix timestamp of the result.

        Returns:
            Integer row ID of the inserted record.

        Raises:
            RuntimeError: If the store is not initialized.
            sqlite3.Error: If the insert fails.

        """
        if self._conn is None:
            msg = "ResultStore.save_result(): not initialized"
            raise RuntimeError(msg)
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT INTO search_results (query, address, score, snippet, timestamp)"
            " VALUES (?, ?, ?, ?, ?)",
            (query, address, score, snippet, timestamp),
        )
        self._conn.commit()
        return int(cursor.lastrowid or 0)

    def get_results(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch cached search results for a query, sorted by score descending.

        Args:
            query: The search query to look up.
            limit: Maximum number of results to return.

        Returns:
            List of result dicts with keys: id, query, address, score,
            snippet, timestamp.

        Raises:
            RuntimeError: If the store is not initialized.

        """
        if self._conn is None:
            msg = "ResultStore.get_results(): not initialized"
            raise RuntimeError(msg)
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT id, query, address, score, snippet, timestamp"
            "  FROM search_results"
            " WHERE query = ?"
            " ORDER BY score DESC"
            " LIMIT ?",
            (query, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def save_session(self, session_id: str, data: str) -> None:
        """Upsert a session record.

        Args:
            session_id: Unique session identifier.
            data: Serialized session data string.

        Raises:
            RuntimeError: If the store is not initialized.

        """
        if self._conn is None:
            msg = "ResultStore.save_session(): not initialized"
            raise RuntimeError(msg)
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (session_id, data, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(session_id) DO UPDATE SET data=excluded.data,"
            "   updated_at=excluded.updated_at",
            (session_id, data, time.time()),
        )
        self._conn.commit()

    def get_session(self, session_id: str) -> str | None:
        """Fetch session data by ID.

        Args:
            session_id: Unique session identifier.

        Returns:
            Serialized session data string, or None if not found.

        Raises:
            RuntimeError: If the store is not initialized.

        """
        if self._conn is None:
            msg = "ResultStore.get_session(): not initialized"
            raise RuntimeError(msg)
        cursor = self._conn.cursor()
        cursor.execute("SELECT data FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        return str(row["data"]) if row else None

    def delete_expired_sessions(self, max_age_seconds: int = 86400) -> int:
        """Delete sessions older than ``max_age_seconds`` and return the count.

        Args:
            max_age_seconds: Maximum session age in seconds before deletion.

        Returns:
            Number of sessions deleted.

        Raises:
            RuntimeError: If the store is not initialized.

        """
        if self._conn is None:
            msg = "ResultStore.delete_expired_sessions(): not initialized"
            raise RuntimeError(msg)
        cutoff = time.time() - max_age_seconds
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE updated_at < ?", (cutoff,))
        self._conn.commit()
        deleted: int = cursor.rowcount
        logger.info("ResultStore: deleted %d expired sessions", deleted)
        return deleted
