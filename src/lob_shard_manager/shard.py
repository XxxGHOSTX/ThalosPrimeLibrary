from typing import Any, Dict, List, Optional


class Shard:

    def __init__(self, shard_id: str, capacity: int = 100) -> None:

        self.shard_id = shard_id

        self.capacity = capacity

        self.entries: Dict[str, Any] = {}



    def is_full(self) -> bool:

        return len(self.entries) >= self.capacity



    def add(self, key: str, value: Any) -> bool:

        if self.is_full() and key not in self.entries:

            return False

        self.entries[key] = value

        return True



    def get(self, key: str, default: Any = None) -> Any:

        return self.entries.get(key, default)



    def keys(self) -> List[str]:

        return list(self.entries.keys())



    def size(self) -> int:

        return len(self.entries)



