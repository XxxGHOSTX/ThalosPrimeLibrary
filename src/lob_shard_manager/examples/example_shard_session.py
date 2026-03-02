from src.lob_shard_manager.shard_manager import ShardManager





manager = ShardManager(capacity=2)



print("Adding entries...")

print("alpha ->", manager.add_entry("alpha", "A"))

print("beta ->", manager.add_entry("beta", "B"))

print("gamma ->", manager.add_entry("gamma", "C"))



print("\nLookup...")

print("alpha:", manager.get_entry("alpha"))

print("missing:", manager.get_entry("missing"))



print("\nShards:", manager.list_shards())

print("Stats:", manager.shard_stats())




