"""Append-only event log stored as JSONL files per graph ID."""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from pathlib import Path

from thalos_prime.storage.provider import get_storage_base_path


@dataclass
class LogEvent:
    """A single entry in the event log.

    Captures an event type, associated graph, timestamp, version,
    and arbitrary payload data.
    """

    event_type: str
    graph_id: str
    timestamp: str
    version: int
    payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Serialize this event to a JSON-safe dictionary.

        Returns:
            Dictionary representation of this log event.

        """
        return {
            "event_type": self.event_type,
            "graph_id": self.graph_id,
            "timestamp": self.timestamp,
            "version": self.version,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> LogEvent:
        """Deserialize a LogEvent from a dictionary produced by to_dict().

        Args:
            d: Dictionary in the format produced by to_dict().

        Returns:
            Reconstructed LogEvent instance.

        """
        raw_payload = d.get("payload", {})
        payload: dict[str, object] = dict(raw_payload) if isinstance(raw_payload, dict) else {}
        return cls(
            event_type=str(d["event_type"]),
            graph_id=str(d["graph_id"]),
            timestamp=str(d["timestamp"]),
            version=int(str(d.get("version", 0))),
            payload=payload,
        )


class EventLog:
    """Append-only event log stored as JSONL (one JSON object per line) per graph.

    Each graph's events are stored in a dedicated ``.jsonl`` file under
    ``base_path/events/{graph_id}.jsonl``.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize the event log with an optional custom base path.

        Args:
            base_path: Root directory for event storage. Uses the default
                from get_storage_base_path() if not provided.

        """
        self._base = (base_path if base_path is not None else get_storage_base_path()) / "events"
        self._base.mkdir(parents=True, exist_ok=True)

    def _log_path(self, graph_id: str) -> Path:
        """Return the JSONL file path for a specific graph.

        Args:
            graph_id: Unique graph identifier.

        Returns:
            Path to the graph's event log file.

        """
        return self._base / f"{graph_id}.jsonl"

    def append(self, event: LogEvent) -> None:
        """Append a LogEvent to the log for its graph_id.

        Args:
            event: LogEvent to append.

        """
        log_path = self._log_path(event.graph_id)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def get_events(self, graph_id: str) -> list[LogEvent]:
        """Return all events for the given graph ID in append order.

        Args:
            graph_id: Unique graph identifier.

        Returns:
            List of LogEvents in the order they were appended.

        """
        log_path = self._log_path(graph_id)
        if not log_path.exists():
            return []
        events: list[LogEvent] = []
        with log_path.open(encoding="utf-8") as fh:
            for raw_line in fh:
                stripped = raw_line.strip()
                if stripped:
                    data: dict[str, object] = json.loads(stripped)
                    events.append(LogEvent.from_dict(data))
        return events

    def log(
        self,
        event_type: str,
        graph_id: str,
        version: int,
        **payload: object,
    ) -> LogEvent:
        """Create and append a new LogEvent, returning it.

        Args:
            event_type: Type label for this event (e.g. ``"graph_created"``).
            graph_id: ID of the graph this event belongs to.
            version: Graph version this event relates to.
            **payload: Arbitrary keyword arguments stored as the event payload.

        Returns:
            The newly created and appended LogEvent.

        """
        event = LogEvent(
            event_type=event_type,
            graph_id=graph_id,
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            version=version,
            payload=dict(payload),
        )
        self.append(event)
        return event


__all__ = ["EventLog", "LogEvent"]
