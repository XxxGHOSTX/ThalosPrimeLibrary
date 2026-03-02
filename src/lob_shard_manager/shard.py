class Shard:

    def __init__(self, shard_id, capacity=100):

        self.shard_id = shard_id

        self.capacity = capacity

        self.entries = {}



    def is_full(self):

        return len(self.entries) >= self.capacity



    def add(self, key, value):

        if self.is_full() and key not in self.entries:

            return False

        self.entries[key] = value

        return True



    def get(self, key, default=None):

        return self.entries.get(key, default)



    def keys(self):

        return list(self.entries.keys())



    def size(self):

        return len(self.entries)



