import unittest



from src.lob_shard_manager.shard_manager import ShardManager





class TestShardManager(unittest.TestCase):

    def test_add_and_get(self):

        manager = ShardManager(capacity=2)

        shard_a = manager.add_entry("a", 1)

        shard_b = manager.add_entry("b", 2)

        shard_c = manager.add_entry("c", 3)



        self.assertTrue(shard_a)

        self.assertTrue(shard_b)

        self.assertTrue(shard_c)

        self.assertNotEqual(shard_a, shard_c)

        self.assertEqual(manager.get_entry("b"), 2)

        self.assertIsNone(manager.get_entry("missing"))





if __name__ == "__main__":

    unittest.main()





