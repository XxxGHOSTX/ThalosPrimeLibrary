"""Append-only audit ledger for high-level operational events."""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from pathlib import Path

from thalos_prime.storage.provider import get_storage_base_path


@dataclass
class AuditEvent:
    """A single entry in the audit ledger.

    Captures the event type, optional graph association, timestamp,
    and arbitrary detail data.
    """

    event_type: str
    graph_id: str | None
    timestamp: str
    details: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Serialize this event to a JSON-safe dictionary.

        Returns:
            Dictionary representation of this audit event.

        """
        return {
            "event_type": self.event_type,
            "graph_id": self.graph_id,
            "timestamp": self.timestamp,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> AuditEvent:
        """Deserialize an AuditEvent from a dictionary produced by to_dict().

        Args:
            d: Dictionary in the format produced by to_dict().

        Returns:
            Reconstructed AuditEvent instance.

        """
        raw_details = d.get("details", {})
        details: dict[str, object] = dict(raw_details) if isinstance(raw_details, dict) else {}
        return cls(
            event_type=str(d["event_type"]),
            graph_id=str(d["graph_id"]) if d.get("graph_id") is not None else None,
            timestamp=str(d["timestamp"]),
            details=details,
        )


class AuditLedger:
    """Append-only ledger of high-level operational events.

    All events are stored in a single JSONL file at
    ``base_path/audit/ledger.jsonl``.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize the audit ledger with an optional custom base path.

        Args:
            base_path: Root directory for audit storage. Uses the default
                from get_storage_base_path() if not provided.

        """
        audit_dir = (base_path if base_path is not None else get_storage_base_path()) / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        self._ledger_path = audit_dir / "ledger.jsonl"

    def append(
        self,
        event_type: str,
        graph_id: str | None = None,
        **details: object,
    ) -> AuditEvent:
        """Create and append a new audit event, returning it.

        Args:
            event_type: Type label for this event (e.g. ``"graph_executed"``).
            graph_id: Optional ID of the related graph.
            **details: Arbitrary keyword arguments stored as event details.

        Returns:
            The newly created and appended AuditEvent.

        """
        event = AuditEvent(
            event_type=event_type,
            graph_id=graph_id,
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            details=dict(details),
        )
        with self._ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def get_all(self) -> list[AuditEvent]:
        """Return all audit events in append order.

        Returns:
            List of all AuditEvents recorded in the ledger.

        """
        if not self._ledger_path.exists():
            return []
        events: list[AuditEvent] = []
        with self._ledger_path.open(encoding="utf-8") as fh:
            for raw_line in fh:
                stripped = raw_line.strip()
                if stripped:
                    data: dict[str, object] = json.loads(stripped)
                    events.append(AuditEvent.from_dict(data))
        return events

    def get_by_graph(self, graph_id: str) -> list[AuditEvent]:
        """Return all audit events associated with a specific graph ID.

        Args:
            graph_id: Unique graph identifier to filter by.

        Returns:
            List of AuditEvents where graph_id matches.

        """
        return [e for e in self.get_all() if e.graph_id == graph_id]


__all__ = ["AuditEvent", "AuditLedger"]
