"""SQLite-backed durable store for Thalos Prime epistemic state.

The store uses only the Python standard library. It provides:

- durable JSON records for artifacts, snapshots, claims, evidence, evaluations,
  manifests, and proof bundles;
- append-only event persistence;
- optimistic concurrency through expected stream versions;
- idempotency receipts for externally initiated write operations;
- atomic transactions and deterministic JSON serialization.

SQLite is the reference single-node implementation. The interfaces and table
layout are intentionally simple so PostgreSQL or another transactional store can
replace it without changing the epistemic domain model.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from thalos_prime.epistemic_core import BeliefEvent, canonical_json, sha256_hex


class OptimisticConcurrencyError(RuntimeError):
    """Raised when a writer uses a stale expected stream version."""


class IdempotencyConflict(RuntimeError):
    """Raised when an idempotency key is reused with a different request."""


class SqliteEpistemicStore:
    """Durable repository and event store backed by SQLite."""

    _KINDS = {
        "artifact",
        "snapshot",
        "claim",
        "evidence",
        "evaluation",
        "manifest",
        "proof_bundle",
    }

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            self.database_path,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._migrate()

    def close(self) -> None:
        """Close the underlying database connection."""
        self._connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run operations atomically using an immediate write transaction."""
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            yield self._connection
        except Exception:
            self._connection.execute("ROLLBACK")
            raise
        else:
            self._connection.execute("COMMIT")

    def _migrate(self) -> None:
        with self.transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS records (
                    kind TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    PRIMARY KEY (kind, record_id)
                );

                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    claim_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    previous_event_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stream_versions (
                    stream_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS idempotency_receipts (
                    operation TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    PRIMARY KEY (operation, idempotency_key)
                );

                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    def put_record(self, kind: str, record_id: str, payload: Mapping[str, Any]) -> None:
        """Insert or verify an immutable record.

        Re-inserting byte-equivalent content is idempotent. Reusing an identity
        for different content is rejected.
        """
        if kind not in self._KINDS:
            raise ValueError(f"unsupported record kind: {kind}")
        serialized = canonical_json(dict(payload))
        digest = sha256_hex(serialized)
        with self.transaction() as connection:
            existing = connection.execute(
                "SELECT payload_hash FROM records WHERE kind=? AND record_id=?",
                (kind, record_id),
            ).fetchone()
            if existing is not None:
                if str(existing["payload_hash"]) != digest:
                    raise ValueError(f"immutable {kind} identity reused with different content")
                return
            connection.execute(
                "INSERT INTO records(kind, record_id, payload_json, payload_hash) VALUES(?,?,?,?)",
                (kind, record_id, serialized, digest),
            )

    def get_record(self, kind: str, record_id: str) -> dict[str, Any] | None:
        """Return one stored record."""
        row = self._connection.execute(
            "SELECT payload_json FROM records WHERE kind=? AND record_id=?",
            (kind, record_id),
        ).fetchone()
        return None if row is None else dict(json.loads(str(row["payload_json"])))

    def list_records(self, kind: str) -> tuple[dict[str, Any], ...]:
        """Return records in deterministic identifier order."""
        rows = self._connection.execute(
            "SELECT payload_json FROM records WHERE kind=? ORDER BY record_id ASC",
            (kind,),
        ).fetchall()
        return tuple(dict(json.loads(str(row["payload_json"]))) for row in rows)

    def stream_version(self, stream_id: str = "belief-ledger") -> int:
        """Return the current optimistic-concurrency version."""
        row = self._connection.execute(
            "SELECT version FROM stream_versions WHERE stream_id=?",
            (stream_id,),
        ).fetchone()
        return 0 if row is None else int(row["version"])

    def append_event(
        self,
        event: BeliefEvent,
        *,
        expected_version: int,
        stream_id: str = "belief-ledger",
    ) -> int:
        """Persist one event if the stream has the expected version."""
        serialized = canonical_json(event.model_dump(mode="json"))
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT version FROM stream_versions WHERE stream_id=?",
                (stream_id,),
            ).fetchone()
            current = 0 if row is None else int(row["version"])
            if current != expected_version:
                raise OptimisticConcurrencyError(
                    f"expected stream version {expected_version}, current version is {current}"
                )
            if event.sequence != current + 1:
                raise OptimisticConcurrencyError(
                    f"event sequence {event.sequence} does not follow stream version {current}"
                )
            connection.execute(
                """
                INSERT INTO events(
                    sequence, event_id, claim_id, event_type, event_hash,
                    previous_event_hash, payload_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    event.sequence,
                    event.event_id,
                    event.claim_id,
                    event.event_type.value,
                    event.event_hash,
                    event.previous_event_hash,
                    serialized,
                ),
            )
            connection.execute(
                """
                INSERT INTO stream_versions(stream_id, version) VALUES(?,?)
                ON CONFLICT(stream_id) DO UPDATE SET version=excluded.version
                """,
                (stream_id, event.sequence),
            )
        return event.sequence

    def load_events(self) -> tuple[BeliefEvent, ...]:
        """Load the complete event stream in sequence order."""
        rows = self._connection.execute(
            "SELECT payload_json FROM events ORDER BY sequence ASC"
        ).fetchall()
        return tuple(
            BeliefEvent.model_validate(json.loads(str(row["payload_json"])))
            for row in rows
        )

    def get_idempotent_response(
        self,
        operation: str,
        idempotency_key: str,
        request: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        """Return a prior response or reject conflicting key reuse."""
        request_hash = sha256_hex(canonical_json(dict(request)))
        row = self._connection.execute(
            """
            SELECT request_hash, response_json FROM idempotency_receipts
            WHERE operation=? AND idempotency_key=?
            """,
            (operation, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        if str(row["request_hash"]) != request_hash:
            raise IdempotencyConflict(
                f"idempotency key {idempotency_key!r} was already used for another request"
            )
        return dict(json.loads(str(row["response_json"])))

    def save_idempotent_response(
        self,
        operation: str,
        idempotency_key: str,
        request: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> None:
        """Persist an idempotency receipt atomically."""
        request_hash = sha256_hex(canonical_json(dict(request)))
        response_json = canonical_json(dict(response))
        with self.transaction() as connection:
            existing = connection.execute(
                """
                SELECT request_hash FROM idempotency_receipts
                WHERE operation=? AND idempotency_key=?
                """,
                (operation, idempotency_key),
            ).fetchone()
            if existing is not None:
                if str(existing["request_hash"]) != request_hash:
                    raise IdempotencyConflict(
                        f"idempotency key {idempotency_key!r} was already used"
                    )
                return
            connection.execute(
                """
                INSERT INTO idempotency_receipts(
                    operation, idempotency_key, request_hash, response_json
                ) VALUES(?,?,?,?)
                """,
                (operation, idempotency_key, request_hash, response_json),
            )


__all__ = [
    "IdempotencyConflict",
    "OptimisticConcurrencyError",
    "SqliteEpistemicStore",
]
