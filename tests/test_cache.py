"""Tests for the TTLCache in-memory cache module.

Covers lifecycle methods (initialize, validate, operate, reconcile,
checkpoint, terminate), get/put/invalidate/clear operations, TTL
expiry behaviour, max-size eviction, and stats reporting.
"""

import time

import pytest

from thalos_prime.cache.ttl_cache import TTLCache


def test_initialize_creates_empty_store() -> None:
    """initialize() creates an empty internal store."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
    cache.initialize()

    assert cache.stats()["current_size"] == 0
    cache.terminate()


def test_validate_before_initialize_raises() -> None:
    """validate() raises RuntimeError if called before initialize()."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
    with pytest.raises(RuntimeError):
        cache.validate()


def test_validate_after_initialize_passes() -> None:
    """validate() succeeds after initialize()."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
    cache.initialize()
    cache.validate()  # Should not raise
    cache.terminate()


def test_invalid_ttl_raises_on_initialize() -> None:
    """initialize() raises ValueError for ttl_seconds <= 0."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=0, max_size=100)
    with pytest.raises(ValueError):
        cache.initialize()


def test_invalid_max_size_raises_on_initialize() -> None:
    """initialize() raises ValueError for max_size <= 0."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=0)
    with pytest.raises(ValueError):
        cache.initialize()


def test_put_and_get() -> None:
    """put() stores a value and get() retrieves it."""
    cache: TTLCache[str, str] = TTLCache(ttl_seconds=60, max_size=100)
    cache.initialize()

    cache.put("key1", "value1")
    result = cache.get("key1")

    assert result == "value1"
    cache.terminate()


def test_get_missing_key_returns_none() -> None:
    """get() returns None for absent keys."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
    cache.initialize()

    assert cache.get("nonexistent") is None
    cache.terminate()


def test_get_expired_entry_returns_none() -> None:
    """get() returns None and evicts entries that have exceeded TTL."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=1, max_size=100)
    cache.initialize()

    cache.put("expiring", 42)
    time.sleep(1.1)
    result = cache.get("expiring")

    assert result is None
    assert cache.stats()["evictions"] == 1
    cache.terminate()


def test_invalidate_removes_key() -> None:
    """invalidate() removes a specific key and returns True."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
    cache.initialize()

    cache.put("remove_me", 99)
    removed = cache.invalidate("remove_me")

    assert removed is True
    assert cache.get("remove_me") is None
    cache.terminate()


def test_invalidate_absent_key_returns_false() -> None:
    """invalidate() returns False when the key is not in the cache."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
    cache.initialize()

    assert cache.invalidate("absent") is False
    cache.terminate()


def test_clear_removes_all_entries() -> None:
    """clear() removes all entries without resetting hit/miss stats."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
    cache.initialize()

    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")
    cache.clear()

    assert cache.stats()["current_size"] == 0
    assert cache.stats()["hits"] == 1  # Stats are preserved
    cache.terminate()


def test_max_size_evicts_oldest() -> None:
    """put() evicts the oldest entry when max_size is reached."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=3)
    cache.initialize()

    cache.put("first", 1)
    cache.put("second", 2)
    cache.put("third", 3)
    cache.put("fourth", 4)  # Should evict "first"

    assert cache.get("first") is None
    assert cache.get("second") == 2
    assert cache.get("fourth") == 4
    assert cache.stats()["evictions"] >= 1
    cache.terminate()


def test_stats_tracks_hits_and_misses() -> None:
    """stats() accurately tracks hit and miss counts."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
    cache.initialize()

    cache.put("x", 10)
    cache.get("x")      # hit
    cache.get("x")      # hit
    cache.get("y")      # miss

    s = cache.stats()
    assert s["hits"] == 2
    assert s["misses"] == 1
    cache.terminate()


def test_reconcile_evicts_expired() -> None:
    """reconcile() removes all entries that have exceeded TTL."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=1, max_size=100)
    cache.initialize()

    cache.put("a", 1)
    cache.put("b", 2)
    time.sleep(1.1)
    cache.reconcile()

    assert cache.stats()["current_size"] == 0
    assert cache.stats()["evictions"] == 2
    cache.terminate()


def test_operate_is_noop() -> None:
    """operate() is a no-op and does not raise."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
    cache.initialize()
    cache.operate()  # Should not raise
    cache.terminate()


def test_checkpoint_returns_stats_dict() -> None:
    """checkpoint() returns a dict with cache metadata."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=30, max_size=50)
    cache.initialize()
    cache.put("k", 1)

    state = cache.checkpoint()

    assert state["component"] == "TTLCache"
    assert state["ttl_seconds"] == 30
    assert state["max_size"] == 50
    assert state["current_size"] == 1
    cache.terminate()


def test_terminate_clears_store() -> None:
    """terminate() clears all entries and resets initialized flag."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
    cache.initialize()
    cache.put("k", 1)
    cache.terminate()

    # Validate should raise after terminate
    with pytest.raises(RuntimeError):
        cache.validate()


def test_put_overwrites_existing_key() -> None:
    """put() overwrites an existing key with a new value."""
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
    cache.initialize()

    cache.put("key", 1)
    cache.put("key", 2)

    assert cache.get("key") == 2
    cache.terminate()


def test_generic_types() -> None:
    """TTLCache works with non-string key and value types."""
    cache: TTLCache[int, list[str]] = TTLCache(ttl_seconds=60, max_size=10)
    cache.initialize()

    cache.put(1, ["a", "b"])
    cache.put(2, ["c"])

    assert cache.get(1) == ["a", "b"]
    assert cache.get(2) == ["c"]
    assert cache.get(3) is None
    cache.terminate()
