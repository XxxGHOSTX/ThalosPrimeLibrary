"""Thalos Prime cache subsystem.

Exports the generic TTLCache for use throughout the Thalos Prime pipeline
and API layers.
"""

from thalos_prime.cache.ttl_cache import TTLCache

__all__ = ["TTLCache"]
