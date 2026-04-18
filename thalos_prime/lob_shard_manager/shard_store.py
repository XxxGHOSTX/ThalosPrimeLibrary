"""Shard store for deterministic in-memory shards."""

from __future__ import annotations

from thalos_prime.lob_shard_manager.shard import Shard


class ShardStore:
    """Store and retrieve shard objects."""

    def __init__(self) -> None:
        self.shards: dict[str, Shard] = {}

    def create_shard(self, shard_id: str, capacity: int = 100) -> Shard:
        if shard_id in self.shards:
            return self.shards[shard_id]
        shard = Shard(shard_id, capacity=capacity)
        self.shards[shard_id] = shard
        return shard

    def get_shard(self, shard_id: str) -> Shard | None:
        return self.shards.get(shard_id)

    def list_shards(self) -> list[str]:
        return list(self.shards.keys())
