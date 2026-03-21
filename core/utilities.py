"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def compute_sha256(data: dict | str | bytes) -> str:
    """Compute a SHA-256 hash of a dict, string, or bytes object."""
    if isinstance(data, dict):
        raw = json.dumps(data, sort_keys=True).encode("utf-8")
    elif isinstance(data, str):
        raw = data.encode("utf-8")
    else:
        raw = data
    return hashlib.sha256(raw).hexdigest()


def append_jsonl(path: str | Path, record: dict) -> None:
    """Append a JSON record to a JSONL file atomically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def now_iso() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def load_jsonl(path: str | Path) -> list[dict]:
    """Load all records from a JSONL file."""
    path = Path(path)
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def validate_seed(seed: int | None, min_bits: int = 64) -> int:
    """Validate that a seed is a positive non-zero integer of at least min_bits.

    Args:
        seed: The seed value to validate.
        min_bits: Minimum bit size (default 64).

    Returns:
        The validated seed as an int.

    Raises:
        ValueError: If the seed is invalid.
    """
    if seed is None or not isinstance(seed, int) or seed <= 0:
        raise ValueError(f"Invalid seed: {seed}. A positive 64-bit integer is required.")
    max_val = 2**min_bits
    if seed >= max_val:
        raise ValueError(f"Seed {seed} exceeds {min_bits}-bit maximum ({max_val}).")
    return seed
