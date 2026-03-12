"""State backend ABC for infra-synthesis.

Defines the abstract interface for persisting schema snapshots.
All implementations must be JSON-serialisable and atomic.

Control Plane: state coordination only.
"""

from __future__ import annotations

import abc
from typing import Any


class StateBackend(abc.ABC):
    """Abstract base class for schema-snapshot persistence backends."""

    @abc.abstractmethod
    def save(self, key: str, state: dict[str, Any]) -> None:
        """Persist *state* under *key*.

        Args:
            key: Unique identifier for this snapshot (e.g. schema name + version).
            state: Serialisable dict representing the current schema snapshot.

        """

    @abc.abstractmethod
    def load(self, key: str) -> dict[str, Any] | None:
        """Retrieve a previously persisted snapshot.

        Args:
            key: Identifier used when :meth:`save` was called.

        Returns:
            The stored dict, or ``None`` when no snapshot exists for *key*.

        """

    @abc.abstractmethod
    def delete(self, key: str) -> None:
        """Remove the snapshot stored under *key*.

        No-op if *key* does not exist.

        Args:
            key: Identifier of the snapshot to delete.

        """

    @abc.abstractmethod
    def list_keys(self) -> list[str]:
        """Return all keys for which snapshots are currently stored.

        Returns:
            Sorted list of key strings.

        """


__all__ = ["StateBackend"]
