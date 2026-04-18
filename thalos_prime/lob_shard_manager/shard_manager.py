"""Deterministic shard manager."""

from __future__ import annotations

from thalos_prime.lob_shard_manager.shard import Shard
from thalos_prime.lob_shard_manager.shard_store import ShardStore
from thalos_prime.lob_shard_manager.utils import make_shard_id


class ShardManager:
    """Manage key/value entries across bounded shards."""

    def __init__(self, capacity: int = 100, shard_prefix: str = "shard") -> None:
        self.capacity = capacity
        self.shard_prefix = shard_prefix
        self.store = ShardStore()
        self.index: dict[str, str] = {}
        self._next_id = 1

    def _create_shard(self) -> Shard:
        shard_id = make_shard_id(self._next_id, prefix=self.shard_prefix)
        self._next_id += 1
        return self.store.create_shard(shard_id, capacity=self.capacity)

    def _find_or_create_shard(self) -> Shard:
        for shard_id in self.store.list_shards():
            shard = self.store.get_shard(shard_id)
            if shard is not None and not shard.is_full():
                return shard
        return self._create_shard()

    def add_entry(self, key: str, value: object) -> str:
        if key in self.index:
            shard = self.store.get_shard(self.index[key])
            if shard is not None:
                shard.add(key, value)
                return shard.shard_id

        shard = self._find_or_create_shard()
        if not shard.add(key, value):
            shard = self._create_shard()
            shard.add(key, value)
        self.index[key] = shard.shard_id
        return shard.shard_id

    def get_entry(self, key: str, default: object | None = None) -> object | None:
        shard_id = self.index.get(key)
        if shard_id is None:
            return default
        shard = self.store.get_shard(shard_id)
        if shard is None:
            return default
        return shard.get(key, default)

    def find_shard_for_key(self, key: str) -> str | None:
        return self.index.get(key)

    def list_shards(self) -> list[str]:
        return self.store.list_shards()

    def shard_stats(self) -> list[dict[str, object]]:
        stats: list[dict[str, object]] = []
        for shard_id in self.store.list_shards():
            shard = self.store.get_shard(shard_id)
            if shard is not None:
                stats.append({"id": shard_id, "size": shard.size()})
        return stats

    # Lifecycle contract methods
    def initialize(self) -> None:
        """Initialize shard manager state."""
        if not hasattr(self, "store"):
            self.store = ShardStore()
        if not hasattr(self, "index"):
            self.index = {}

    def validate(self) -> bool:
        """Validate shard manager invariants."""
        return self.capacity > 0

    def operate(self) -> list[dict[str, object]]:
        """Operate by returning current shard statistics."""
        return self.shard_stats()

    def reconcile(self) -> None:
        """Reconcile index entries with existing shards."""
        existing_shards = set(self.store.list_shards())
        self.index = {
            key: shard_id for key, shard_id in self.index.items() if shard_id in existing_shards
        }

    def checkpoint(self) -> dict[str, object]:
        """Return serializable state checkpoint."""
        return {
            "capacity": self.capacity,
            "shard_prefix": self.shard_prefix,
            "next_id": self._next_id,
            "index": dict(self.index),
            "shards": self.shard_stats(),
        }

    def terminate(self) -> None:
        """Terminate manager state by clearing in-memory indexes."""
        self.index.clear()
