"""Shard entity for deterministic in-memory shard manager."""

from __future__ import annotations


class Shard:
    """Single shard container."""

    def __init__(self, shard_id: str, capacity: int = 100) -> None:
        self.shard_id = shard_id
        self.capacity = capacity
        self.entries: dict[str, object] = {}

    def is_full(self) -> bool:
        return len(self.entries) >= self.capacity

    def add(self, key: str, value: object) -> bool:
        if self.is_full() and key not in self.entries:
            return False
        self.entries[key] = value
        return True

    def get(self, key: str, default: object | None = None) -> object | None:
        return self.entries.get(key, default)

    def keys(self) -> list[str]:
        return list(self.entries.keys())

    def size(self) -> int:
        return len(self.entries)
