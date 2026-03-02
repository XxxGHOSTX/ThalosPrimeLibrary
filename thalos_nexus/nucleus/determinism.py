"""Thalos Prime NEXUS Core v1 — Determinism Nucleus.

Provides deterministic hashing primitives, run-ID computation, canonical JSON
serialisation, and the hash-chained event-log writer/verifier used throughout
the NEXUS pipeline.

Control Plane boundary: pure computation — no I/O side-effects except the
EventLogWriter which explicitly manages a single append-only JSONL file.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GENESIS_PREV_HASH: str = "0" * 64


def compute_sha256(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *data*.

    Args:
        data: Raw bytes to hash.

    Returns:
        64-character lowercase hexadecimal string.

    """
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: dict[str, Any]) -> bytes:
    """Serialise *obj* to canonical JSON bytes (sorted keys, no whitespace).

    Args:
        obj: Dictionary to serialise.

    Returns:
        UTF-8 encoded bytes of the canonical JSON representation.

    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def compute_config_hash(config: dict[str, Any]) -> str:
    """Return the SHA-256 of the canonical JSON representation of *config*.

    Args:
        config: Configuration mapping to hash.

    Returns:
        64-character lowercase hexadecimal SHA-256 digest.

    """
    return compute_sha256(canonical_json(config))


def compute_run_id(seed: int, task: str, genome_hash: str, config_hash: str) -> str:
    """Compute a deterministic run identifier.

    The run_id is the SHA-256 of the UTF-8 encoding of
    ``"{seed}:{task}:{genome_hash}:{config_hash}"``.

    Args:
        seed: Integer random seed for the run.
        task: Task descriptor string.
        genome_hash: SHA-256 hex of the genome file.
        config_hash: SHA-256 hex of the configuration mapping.

    Returns:
        64-character lowercase hexadecimal SHA-256 run identifier.

    """
    raw = f"{seed}:{task}:{genome_hash}:{config_hash}"
    return compute_sha256(raw.encode())


class EventLogWriter:
    """Append-only hash-chained JSONL event log writer.

    Each entry's ``chain_hash`` is the SHA-256 of the concatenation of
    the previous entry's ``chain_hash`` bytes and the canonical JSON of
    the current entry's *core* fields (seq, timestamp, event_type,
    payload, prev_hash).  This produces a tamper-evident chain rooted at
    :data:`GENESIS_PREV_HASH`.

    Args:
        path: Path to the JSONL output file.  The file is created on first
              append; its parent directory must already exist.

    """

    def __init__(self, path: Path) -> None:
        """Initialise the writer for *path*."""
        self._path = path
        self._seq: int = 0
        self._prev_hash: str = GENESIS_PREV_HASH
        logger.debug("EventLogWriter initialised at %s", path)

    def append(self, event_type: str, payload: dict[str, Any]) -> str:
        """Append a new entry to the event log and return its chain_hash.

        Args:
            event_type: Non-empty event type string.
            payload: Arbitrary JSON-serialisable payload mapping.

        Returns:
            The ``chain_hash`` of the appended entry.

        Raises:
            ValueError: If *event_type* is empty.

        """
        if not event_type:
            raise ValueError("event_type must be a non-empty string")

        timestamp = datetime.now(UTC).isoformat()
        entry_core: dict[str, Any] = {
            "seq": self._seq,
            "timestamp": timestamp,
            "event_type": event_type,
            "payload": payload,
            "prev_hash": self._prev_hash,
        }
        chain_input = self._prev_hash.encode() + canonical_json(entry_core)
        chain_hash = compute_sha256(chain_input)

        entry: dict[str, Any] = {**entry_core, "chain_hash": chain_hash}

        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")

        self._seq += 1
        self._prev_hash = chain_hash
        return chain_hash

    def current_hash(self) -> str:
        """Return the chain_hash of the most recently appended entry.

        Returns:
            The current chain tip hash (GENESIS_PREV_HASH if no entries written).

        """
        return self._prev_hash


class EventLogVerifier:
    """Verifies the integrity of a hash-chained JSONL event log.

    Reads the log produced by :class:`EventLogWriter` and re-derives each
    entry's ``chain_hash`` to confirm the chain has not been tampered with.
    """

    def verify(self, path: Path) -> list[str]:
        """Verify the hash chain of the event log at *path*.

        Args:
            path: Path to the JSONL event log file.

        Returns:
            A list of error strings.  An empty list means the chain is valid.

        """
        errors: list[str] = []
        if not path.exists():
            return [f"Event log not found: {path}"]

        prev_hash = GENESIS_PREV_HASH
        with path.open("r", encoding="utf-8") as fh:
            for lineno, raw_line in enumerate(fh, start=1):
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    entry: dict[str, Any] = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    errors.append(f"Line {lineno}: JSON parse error: {exc}")
                    continue

                stored_chain = entry.get("chain_hash", "")
                entry_core: dict[str, Any] = {
                    "seq": entry.get("seq"),
                    "timestamp": entry.get("timestamp"),
                    "event_type": entry.get("event_type"),
                    "payload": entry.get("payload"),
                    "prev_hash": entry.get("prev_hash"),
                }
                chain_input = prev_hash.encode() + canonical_json(entry_core)
                expected = compute_sha256(chain_input)

                if stored_chain != expected:
                    errors.append(
                        f"Line {lineno} seq={entry.get('seq')}: "
                        f"chain_hash mismatch — stored={stored_chain!r} "
                        f"expected={expected!r}"
                    )

                prev_hash = stored_chain or prev_hash

        return errors
