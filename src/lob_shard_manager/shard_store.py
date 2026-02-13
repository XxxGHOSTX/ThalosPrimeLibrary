from .shard import Shard





class ShardStore:

    def __init__(self):

        self.shards = {}



    def create_shard(self, shard_id, capacity=100):

        if shard_id in self.shards:

            return self.shards[shard_id]

        shard = Shard(shard_id, capacity=capacity)

        self.shards[shard_id] = shard

        return shard



    def get_shard(self, shard_id):

        return self.shards.get(shard_id)



    def list_shards(self):

        return list(self.shards.keys())





