"""Structured cognitive exchange and evolution memory."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid


@dataclass
class MemoryEntry:
    memory_id: str
    type: str
    content: Any
    created_by: str
    confidence: float
    tags: tuple[str, ...] = ()
    scope: str = "global"
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    evidence: tuple[str, ...] = ()


class CognitiveMemory:
    """Layered short/mid/long-term memory with deterministic ranking."""

    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []
        self._evolution: list[dict[str, Any]] = []

    def publish(
        self, type: str, content: Any, created_by: str, confidence: float = 0.5,
        tags: tuple[str, ...] = (), scope: str = "global", evidence: tuple[str, ...] = (),
    ) -> MemoryEntry:
        entry = MemoryEntry(
            memory_id=str(uuid.uuid4()), type=type, content=content,
            created_by=created_by, confidence=max(0.0, min(1.0, confidence)),
            tags=tags, scope=scope, evidence=evidence,
        )
        self._entries.append(entry)
        return entry

    def query(self, query: str = "", type: str | None = None, limit: int = 20) -> list[MemoryEntry]:
        tokens = set(query.lower().split())
        candidates = [e for e in self._entries if type is None or e.type == type]

        def rank(entry: MemoryEntry) -> tuple[float, str]:
            haystack = f"{entry.content} {' '.join(entry.tags)}".lower()
            overlap = sum(token in haystack for token in tokens)
            return (entry.confidence + overlap * 0.1, entry.memory_id)

        return sorted(candidates, key=rank, reverse=True)[:limit]

    def record_evolution(self, event: dict[str, Any]) -> None:
        self._evolution.append(dict(event))

    def evolution_history(self) -> list[dict[str, Any]]:
        return [dict(event) for event in self._evolution]

    def snapshot(self) -> dict[str, Any]:
        return {
            "entries": [asdict(entry) for entry in self._entries],
            "evolution": self.evolution_history(),
        }
