"""Snapshot helper for rollback manager.

Captures a point-in-time snapshot of the schema and persists it via
the configured :class:`StateBackend`.

Data Plane helper: state serialisation only.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from thalos_prime.infra_synthesis.state.backend import StateBackend

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Captures and restores schema snapshots via a :class:`StateBackend`.

    Args:
        backend: Configured state backend for persistence.

    """

    def __init__(self, backend: StateBackend) -> None:
        """Initialise with *backend*.

        Args:
            backend: State backend for snapshot persistence.

        """
        self._backend = backend

    def capture(self, key: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Capture a snapshot of *schema* and persist it under *key*.

        Args:
            key: Unique identifier for this snapshot.
            schema: Schema dict to snapshot.

        Returns:
            The stored snapshot dict (includes a ``_captured_at`` timestamp).

        """
        snapshot: dict[str, Any] = {
            "_captured_at": datetime.now(UTC).isoformat(),
            **schema,
        }
        self._backend.save(key, snapshot)
        logger.info("SnapshotManager: captured snapshot '%s'", key)
        return snapshot

    def restore(self, key: str) -> dict[str, Any]:
        """Restore and return the snapshot stored under *key*.

        Args:
            key: Identifier used when :meth:`capture` was called.

        Returns:
            Stored snapshot dict.

        Raises:
            KeyError: When no snapshot exists for *key*.

        """
        snapshot = self._backend.load(key)
        if snapshot is None:
            msg = f"No snapshot found for key '{key}'"
            raise KeyError(msg)
        logger.info("SnapshotManager: restored snapshot '%s'", key)
        return snapshot


__all__ = ["SnapshotManager"]
