from typing import Dict, List, Optional

from .shard import Shard





class ShardStore:

    def __init__(self) -> None:

        self.shards: Dict[str, Shard] = {}



    def create_shard(self, shard_id: str, capacity: int = 100) -> Shard:

        if shard_id in self.shards:

            return self.shards[shard_id]

        shard = Shard(shard_id, capacity=capacity)

        self.shards[shard_id] = shard

        return shard



    def get_shard(self, shard_id: str) -> Optional[Shard]:

        return self.shards.get(shard_id)



    def list_shards(self) -> List[str]:

        return list(self.shards.keys())





