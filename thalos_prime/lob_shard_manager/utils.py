"""Utilities for shard manager."""

from __future__ import annotations


def make_shard_id(index: int, prefix: str = "shard") -> str:
    """Return deterministic shard identifier."""
    return f"{prefix}_{index}"
