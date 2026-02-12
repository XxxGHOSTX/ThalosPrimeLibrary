"""State store for persisting session and seed data."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class StateStore:
    """SQLite-based state store for session data."""

    def __init__(self, db_path: Path) -> None:
        """Initialize state store."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                last_active TEXT NOT NULL
            )
        """)

        # Seeds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_input TEXT NOT NULL,
                seed INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_seeds_session 
            ON seeds(session_id, timestamp DESC)
        """)

        conn.commit()
        conn.close()

    def create_session(self, session_id: str) -> None:
        """Create a new session."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        timestamp = datetime.utcnow().isoformat()

        cursor.execute(
            """
            INSERT OR IGNORE INTO sessions (session_id, created_at, last_active)
            VALUES (?, ?, ?)
        """,
            (session_id, timestamp, timestamp),
        )

        conn.commit()
        conn.close()

    def update_session_activity(self, session_id: str) -> None:
        """Update session last active timestamp."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        timestamp = datetime.utcnow().isoformat()

        cursor.execute(
            """
            UPDATE sessions 
            SET last_active = ?
            WHERE session_id = ?
        """,
            (timestamp, session_id),
        )

        conn.commit()
        conn.close()

    def store_seed(self, session_id: str, user_input: str, seed: int) -> None:
        """Store a seed for a session."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        timestamp = datetime.utcnow().isoformat()

        cursor.execute(
            """
            INSERT INTO seeds (session_id, user_input, seed, timestamp)
            VALUES (?, ?, ?, ?)
        """,
            (session_id, user_input, seed, timestamp),
        )

        conn.commit()
        conn.close()

    def get_last_seed(self, session_id: str) -> Optional[int]:
        """Get the last seed for a session."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT seed FROM seeds
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """,
            (session_id,),
        )

        row = cursor.fetchone()
        conn.close()

        return row[0] if row else None

    def get_session_seeds(self, session_id: str, limit: int = 10) -> list[dict[str, any]]:
        """Get recent seeds for a session."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_input, seed, timestamp
            FROM seeds
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (session_id, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_all_sessions(self) -> list[dict[str, str]]:
        """Get all sessions."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id, created_at, last_active
            FROM sessions
            ORDER BY last_active DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def close(self) -> None:
        """Close any open connections (for cleanup)."""
        pass
