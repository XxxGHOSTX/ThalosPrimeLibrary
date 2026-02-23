"""Deterministic in-memory TTL cache for Thalos Prime.

Provides a generic, lifecycle-managed TTL (time-to-live) cache that evicts
entries on expiry and enforces a maximum size bound. Replaces the ad-hoc
``_SEARCH_CACHE`` dict described in ARCHITECTURE.md with a proper component.

Data Plane boundary: cache is passive storage - no lifecycle orchestration
or control-plane coordination logic belongs here.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class TTLCache[K, V]:
    """Generic in-memory cache with time-to-live eviction and bounded size.

    Entries expire after ``ttl_seconds`` seconds. When the cache is full,
    the oldest entry (by insertion order) is evicted to make room.

    Type Parameters:
        K: The key type (must be hashable).
        V: The value type.

    Example::

        cache: TTLCache[str, int] = TTLCache(ttl_seconds=60, max_size=100)
        cache.initialize()
        cache.put("answer", 42)
        value = cache.get("answer")  # 42, or None if expired

    """

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000) -> None:
        """Initialize the TTL cache configuration.

        Args:
            ttl_seconds: Number of seconds before an entry expires. Must be > 0.
            max_size: Maximum number of entries before eviction. Must be > 0.

        """
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        # Populated by initialize()
        self._store: dict[K, tuple[V, float]] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle protocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Allocate internal storage and reset counters.

        Raises:
            ValueError: If ttl_seconds or max_size are invalid.

        """
        if self._ttl_seconds <= 0:
            msg = f"TTLCache: ttl_seconds must be > 0, got {self._ttl_seconds}"
            raise ValueError(msg)
        if self._max_size <= 0:
            msg = f"TTLCache: max_size must be > 0, got {self._max_size}"
            raise ValueError(msg)

        self._store = {}
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._initialized = True
        logger.info(
            "TTLCache initialized: ttl=%ds max_size=%d",
            self._ttl_seconds,
            self._max_size,
        )

    def validate(self) -> None:
        """Verify that the cache is properly initialized and invariants hold.

        Raises:
            RuntimeError: If not initialized.
            ValueError: If configuration invariants are violated.

        """
        if not self._initialized:
            msg = "TTLCache.validate(): not initialized — call initialize() first"
            raise RuntimeError(msg)
        if self._ttl_seconds <= 0:
            msg = f"TTLCache.validate(): ttl_seconds invariant violated: {self._ttl_seconds}"
            raise ValueError(msg)
        if self._max_size <= 0:
            msg = f"TTLCache.validate(): max_size invariant violated: {self._max_size}"
            raise ValueError(msg)
        logger.debug("TTLCache validation passed: size=%d", len(self._store))

    def operate(self) -> None:
        """No-op: cache is passive and serves requests on demand."""
        logger.debug("TTLCache.operate(): no-op (passive component)")

    def reconcile(self) -> None:
        """Evict all entries that have exceeded their TTL.

        Idempotent: safe to call at any time to prune stale entries.
        """
        now = time.monotonic()
        expired_keys = [k for k, (_, ts) in self._store.items() if now - ts > self._ttl_seconds]
        for key in expired_keys:
            del self._store[key]
            self._evictions += 1
        if expired_keys:
            logger.info("TTLCache.reconcile(): evicted %d expired entries", len(expired_keys))

    def checkpoint(self) -> dict[str, object]:
        """Return current cache statistics (does not include cached values).

        Returns:
            Dictionary with hits, misses, evictions, and current_size.

        """
        return {
            "component": "TTLCache",
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "current_size": len(self._store),
            "ttl_seconds": self._ttl_seconds,
            "max_size": self._max_size,
        }

    def terminate(self) -> None:
        """Clear all cached entries and reset counters."""
        self._store.clear()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._initialized = False
        logger.info("TTLCache terminated: all entries cleared")

    # ------------------------------------------------------------------
    # Cache operations
    # ------------------------------------------------------------------

    def get(self, key: K) -> V | None:
        """Return the cached value if present and not expired.

        Args:
            key: Cache lookup key.

        Returns:
            Cached value, or None if the key is absent or has expired.

        """
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        value, timestamp = entry
        if time.monotonic() - timestamp > self._ttl_seconds:
            del self._store[key]
            self._evictions += 1
            self._misses += 1
            return None
        self._hits += 1
        return value

    def put(self, key: K, value: V) -> None:
        """Store a value under the given key with the current timestamp.

        If the cache is at maximum capacity, the oldest entry is evicted
        before inserting the new one.

        Args:
            key: Cache key (must be hashable).
            value: Value to cache.

        """
        if key not in self._store and len(self._store) >= self._max_size:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]
            self._evictions += 1
            logger.debug("TTLCache.put(): evicted oldest entry to make room")
        self._store[key] = (value, time.monotonic())

    def invalidate(self, key: K) -> bool:
        """Remove a specific entry from the cache.

        Args:
            key: The key to remove.

        Returns:
            True if the key was present and removed; False otherwise.

        """
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        """Remove all entries from the cache without resetting statistics."""
        self._store.clear()
        logger.debug("TTLCache.clear(): all entries removed")

    def stats(self) -> dict[str, int]:
        """Return cache performance statistics.

        Returns:
            Dictionary with hits, misses, evictions, and current_size.

        """
        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "current_size": len(self._store),
        }
