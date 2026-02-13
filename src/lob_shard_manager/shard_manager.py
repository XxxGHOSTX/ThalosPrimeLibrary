from typing import Any, Dict, List, Optional

from .shard import Shard
from .shard_store import ShardStore

from .utils import make_shard_id





class ShardManager:

    def __init__(self, capacity: int = 100, shard_prefix: str = "shard") -> None:

        self.capacity = capacity

        self.shard_prefix = shard_prefix

        self.store = ShardStore()

        self.index: Dict[str, str] = {}

        self._next_id = 1



    def _create_shard(self) -> Shard:

        shard_id = make_shard_id(self._next_id, prefix=self.shard_prefix)

        self._next_id += 1

        return self.store.create_shard(shard_id, capacity=self.capacity)



    def _find_or_create_shard(self) -> Shard:

        for shard_id in self.store.list_shards():

            shard = self.store.get_shard(shard_id)

            if shard and not shard.is_full():

                return shard

        return self._create_shard()



    def add_entry(self, key: str, value: Any) -> str:

        if key in self.index:

            shard = self.store.get_shard(self.index[key])

            if shard:

                shard.add(key, value)

                return shard.shard_id

        shard = self._find_or_create_shard()

        if not shard.add(key, value):

            shard = self._create_shard()

            shard.add(key, value)

        self.index[key] = shard.shard_id

        return shard.shard_id



    def get_entry(self, key: str, default: Any = None) -> Any:

        shard_id = self.index.get(key)

        if not shard_id:

            return default

        shard = self.store.get_shard(shard_id)

        if not shard:

            return default

        return shard.get(key, default)



    def find_shard_for_key(self, key: str) -> Optional[str]:

        return self.index.get(key)



    def list_shards(self) -> List[str]:

        return self.store.list_shards()



    def shard_stats(self) -> List[Dict[str, Any]]:

        stats: List[Dict[str, Any]] = []

        for shard_id in self.store.list_shards():

            shard = self.store.get_shard(shard_id)

            if shard:

                stats.append({"id": shard_id, "size": shard.size()})

        return stats





