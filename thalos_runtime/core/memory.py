"""Execution memory - Data Plane storage for thalos_runtime.

Stores immutable execution records in a versioned, serializable,
in-memory structure.  Each record captures the task name, payload,
result, and a UTC timestamp for deterministic replay and audit.

Data Plane boundary: this module only stores and retrieves data.
No lifecycle coordination or control-plane logic belongs here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

_MEMORY_VERSION: str = "1.0"


@dataclass(frozen=True)
class ExecutionRecord:
    """Immutable record of a single task execution.

    Attributes:
        id: Unique identifier for this record.
        task: Task name that was executed.
        payload: Input payload used for the execution.
        result: Result produced by the task handler.
        timestamp: UTC timestamp of execution.
        version: Schema version for serialization compatibility.

    """

    id: UUID
    task: str
    payload: dict[str, Any]
    result: Any
    timestamp: datetime
    version: str = _MEMORY_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize this record to a plain dictionary.

        Returns:
            Dictionary representation with all fields serialized to JSON-safe types.

        """
        return {
            "id": str(self.id),
            "task": self.task,
            "payload": self.payload,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
        }


class ExecutionMemory:
    """In-memory store for task execution records.

    Data Plane component: stores and retrieves execution results.
    State is observable, serializable, and versioned.  Records are
    appended in chronological order and never mutated after storage.
    """

    def __init__(self) -> None:
        """Initialize an empty execution memory store."""
        self._records: list[ExecutionRecord] = []
        logger.debug("ExecutionMemory initialized (version=%s)", _MEMORY_VERSION)

    def store(self, task: str, payload: dict[str, Any], result: Any) -> ExecutionRecord:
        """Create and store a new execution record.

        Args:
            task: Task name that was executed.
            payload: Input payload used for the execution.
            result: Result produced by the task handler.

        Returns:
            Newly created, immutable ExecutionRecord with a unique UUID.

        """
        record = ExecutionRecord(
            id=uuid4(),
            task=task,
            payload=payload,
            result=result,
            timestamp=datetime.now(UTC),
        )
        self._records.append(record)
        logger.info(
            "ExecutionMemory: stored record id=%s task=%s",
            record.id,
            task,
        )
        return record

    def get_all(self) -> list[ExecutionRecord]:
        """Return all execution records in chronological order.

        Returns:
            Shallow copy of the full record list.

        """
        return list(self._records)

    def get_by_task(self, task: str) -> list[ExecutionRecord]:
        """Return all records for a specific task name.

        Args:
            task: Task name to filter by.

        Returns:
            Filtered list of matching records in chronological order.

        """
        return [r for r in self._records if r.task == task]

    def checkpoint(self) -> dict[str, Any]:
        """Serialize the full memory state for restart.

        Returns:
            Versioned dict containing all stored records as plain dicts.

        """
        return {
            "version": _MEMORY_VERSION,
            "records": [r.to_dict() for r in self._records],
        }


__all__ = ["ExecutionMemory", "ExecutionRecord"]
