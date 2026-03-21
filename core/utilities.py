"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

import hashlib
import json
from datetime import UTC, datetime
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
    """Append a JSON record to a JSONL file (best-effort, no cross-process locking)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def now_iso() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(UTC).isoformat()


def load_jsonl(path: str | Path) -> list[dict]:
    """Load all records from a JSONL file."""
    path = Path(path)
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def validate_seed(seed: int | None, max_bits: int = 64) -> int:
    """Validate that a seed is a positive integer that fits within max_bits.

    Args:
        seed: The seed value to validate.
        max_bits: Maximum bit width the seed must fit within (default 64).
            A valid seed must satisfy ``1 <= seed < 2**max_bits``.

    Returns:
        The validated seed as an int.

    Raises:
        ValueError: If the seed is None, non-positive, or exceeds the bit limit.
    """
    if seed is None or not isinstance(seed, int) or seed <= 0:
        msg = f"Invalid seed: {seed}. A positive integer is required."
        raise ValueError(msg)
    max_val = 2**max_bits
    if seed >= max_val:
        msg = f"Seed {seed} exceeds {max_bits}-bit maximum ({max_val - 1})."
        raise ValueError(msg)
    return seed
