"""Shared deterministic hashing utilities using SHA-256 and stable JSON serialization."""

from __future__ import annotations

import hashlib
import json


def stable_json(obj: object) -> str:
    """Serialize an object to JSON with sorted keys and compact separators.

    Args:
        obj: Any JSON-serializable Python object.

    Returns:
        Deterministic JSON string with sorted dict keys.

    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str) -> str:
    """Compute the SHA-256 hex digest of a UTF-8 encoded string.

    Args:
        data: Input string to hash.

    Returns:
        Lowercase hex string of the SHA-256 digest.

    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hash_dict(d: dict[str, object]) -> str:
    """Compute a deterministic hash of a dictionary.

    Serializes the dictionary to stable JSON then computes SHA-256.

    Args:
        d: Dictionary to hash. All values must be JSON-serializable.

    Returns:
        Lowercase hex SHA-256 digest of the stable JSON representation.

    """
    return sha256_hex(stable_json(d))


__all__ = ["hash_dict", "sha256_hex", "stable_json"]
