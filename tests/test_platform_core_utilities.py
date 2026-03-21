"""Tests for core.utilities: compute_sha256, append_jsonl, validate_seed, load_jsonl, now_iso."""

import json
from pathlib import Path

import pytest

from core.utilities import (
    append_jsonl,
    compute_sha256,
    load_jsonl,
    now_iso,
    validate_seed,
)


# ---------------------------------------------------------------------------
# compute_sha256
# ---------------------------------------------------------------------------


def test_compute_sha256_dict_deterministic() -> None:
    """Same dict always produces the same hash regardless of key order."""
    h1 = compute_sha256({"b": 2, "a": 1})
    h2 = compute_sha256({"a": 1, "b": 2})
    assert h1 == h2
    assert len(h1) == 64


def test_compute_sha256_string() -> None:
    """String input is accepted and produces a valid hex digest."""
    result = compute_sha256("hello world")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_compute_sha256_bytes() -> None:
    """Bytes input is accepted and produces a valid hex digest."""
    result = compute_sha256(b"raw bytes")
    assert len(result) == 64


def test_compute_sha256_different_inputs_differ() -> None:
    """Different inputs must not produce the same hash."""
    assert compute_sha256("foo") != compute_sha256("bar")


# ---------------------------------------------------------------------------
# validate_seed
# ---------------------------------------------------------------------------


def test_validate_seed_valid() -> None:
    """A valid 64-bit seed is returned unchanged."""
    seed = 12345678901234567
    assert validate_seed(seed) == seed


def test_validate_seed_none_raises() -> None:
    """None seed raises ValueError."""
    with pytest.raises(ValueError, match="Invalid seed"):
        validate_seed(None)


def test_validate_seed_zero_raises() -> None:
    """Zero raises ValueError (must be positive)."""
    with pytest.raises(ValueError, match="Invalid seed"):
        validate_seed(0)


def test_validate_seed_negative_raises() -> None:
    """Negative seed raises ValueError."""
    with pytest.raises(ValueError, match="Invalid seed"):
        validate_seed(-1)


def test_validate_seed_too_large_raises() -> None:
    """Seed >= 2**64 raises ValueError."""
    with pytest.raises(ValueError, match="exceeds 64-bit maximum"):
        validate_seed(2**64)


def test_validate_seed_max_boundary() -> None:
    """Seed == 2**64 - 1 (max valid 64-bit value) is accepted."""
    max_seed = 2**64 - 1
    assert validate_seed(max_seed) == max_seed


# ---------------------------------------------------------------------------
# append_jsonl / load_jsonl
# ---------------------------------------------------------------------------


def test_append_and_load_jsonl(tmp_path: Path) -> None:
    """Records appended with append_jsonl are recoverable via load_jsonl."""
    log = tmp_path / "test.jsonl"
    records = [{"event": "first", "seed": 1}, {"event": "second", "seed": 2}]
    for rec in records:
        append_jsonl(log, rec)

    loaded = load_jsonl(log)
    assert loaded == records


def test_append_jsonl_creates_parent_dirs(tmp_path: Path) -> None:
    """append_jsonl creates missing parent directories."""
    log = tmp_path / "nested" / "dir" / "events.jsonl"
    append_jsonl(log, {"x": 1})
    assert log.exists()


def test_load_jsonl_missing_file(tmp_path: Path) -> None:
    """load_jsonl returns an empty list for a non-existent file."""
    result = load_jsonl(tmp_path / "nonexistent.jsonl")
    assert result == []


# ---------------------------------------------------------------------------
# now_iso
# ---------------------------------------------------------------------------


def test_now_iso_format() -> None:
    """now_iso returns an ISO 8601 string that parses correctly."""
    from datetime import datetime

    ts = now_iso()
    # Should parse without error and contain UTC offset
    dt = datetime.fromisoformat(ts)
    assert dt.utcoffset() is not None
