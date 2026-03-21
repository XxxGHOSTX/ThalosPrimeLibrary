"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

import sqlite3
import json
from pathlib import Path
from datetime import UTC, datetime
from typing import Any


class ThalosStateStore:
    """SQLite WAL-backed state persistence for the Thalos Control Plane."""

    def __init__(self, db_path: str = "STATELOG/state.db") -> None:
        """Initialize the state store and create the schema if needed."""
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        """Create the events table if it does not exist."""
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self.conn.commit()

    def write_event(
        self,
        session_id: str,
        event_type: str,
        payload: dict[str, Any],
        sha256_hash: str,
    ) -> None:
        """Persist an event record to the state store."""
        self.conn.execute(
            "INSERT INTO events (session_id, event_type, payload, sha256_hash, created_at) VALUES (?,?,?,?,?)",
            (
                session_id,
                event_type,
                json.dumps(payload),
                sha256_hash,
                datetime.now(UTC).isoformat(),
            ),
        )
        self.conn.commit()

    def get_events(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve all events for a session in order."""
        cur = self.conn.execute(
            "SELECT event_type, payload, sha256_hash, created_at FROM events WHERE session_id=? ORDER BY id",
            (session_id,),
        )
        return [
            {
                "event_type": r[0],
                "payload": json.loads(r[1]),
                "sha256_hash": r[2],
                "created_at": r[3],
            }
            for r in cur.fetchall()
        ]
