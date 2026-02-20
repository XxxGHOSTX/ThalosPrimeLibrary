import unittest

from src.lob_shard_manager.shard_manager import ShardManager


class TestShardManager(unittest.TestCase):

    def test_add_and_get(self):

        manager = ShardManager(capacity=2)

        shard_a = manager.add_entry("a", 1)

        shard_b = manager.add_entry("b", 2)

        shard_c = manager.add_entry("c", 3)



        assert shard_a

        assert shard_b

        assert shard_c

        assert shard_a != shard_c

        assert manager.get_entry("b") == 2

        assert manager.get_entry("missing") is None





if __name__ == "__main__":

    unittest.main()





