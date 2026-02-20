"""
Deterministic ingestion and canonicalization utilities for Thalos Prime.

This module implements the ingestion-layer responsibilities described in the
repository specification:
- Normalize fragmented input into a canonical, reproducible form.
- Compute deterministic semantic addresses (`meaning_hash`) derived from the
  normalized representation.
- Provide an explicit artifact record that can be serialized, validated, and
  replayed without nondeterministic state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
import unicodedata
from typing import Any, Dict, List


_WHITESPACE_RE = re.compile(r"\s+")

# Curly quotes and common dash variants are collapsed to deterministic ASCII
_CANONICAL_REPLACEMENTS: Dict[str, str] = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2014": "-",
    "\u2013": "-",
}

NORMALIZATION_VERSION = "1.0.0"
SEMANTIC_SCHEMA_VERSION = "1.0.0"


def canonicalize_text(text: str) -> str:
    """
    Deterministically normalize input text.

    Steps:
    - Unicode NFC normalization
    - Replace typographic quotes/dashes with ASCII equivalents
    - Lowercase
    - Collapse all whitespace to single spaces and strip edges
    """
    normalized = unicodedata.normalize("NFC", text)
    for src, target in _CANONICAL_REPLACEMENTS.items():
        normalized = normalized.replace(src, target)
    normalized = normalized.lower()
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def _tokenize(text: str) -> List[str]:
    """Simple deterministic tokenization that preserves ordering."""
    if not text:
        return []
    return text.split(" ")


def _normalized_representation(
    normalized_text: str, tokens: List[str], metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build the canonical representation that is hashed to produce a meaning hash.

    The representation is intentionally small and fully serializable to ensure
    reproducible hashing across platforms.
    """
    return {
        "normalized_text": normalized_text,
        "tokens": tokens,
        "schema_version": SEMANTIC_SCHEMA_VERSION,
        "metadata": metadata,
    }


def compute_meaning_hash(normalized_repr: Dict[str, Any]) -> str:
    """
    Compute the deterministic meaning hash for a normalized representation.

    The representation must already be normalized and free of nondeterministic
    fields; this function only performs a stable JSON serialization and SHA256.
    """
    serialized = json.dumps(normalized_repr, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CanonicalArtifact:
    """Immutable ingestion artifact with deterministic addressing."""

    artifact_id: str
    raw_text: str
    normalized_text: str
    tokens: List[str]
    meaning_hash: str
    metadata: Dict[str, Any]


def ingest_fragment(
    raw_text: str,
    *,
    source: str,
    created_at: datetime | None = None,
    metadata: Dict[str, Any] | None = None,
) -> CanonicalArtifact:
    """
    Ingest a raw fragment into a deterministic CanonicalArtifact.

    - Normalizes text deterministically.
    - Derives a stable artifact_id from the normalized text.
    - Computes a meaning_hash from the normalized representation, including the
      schema version and supplied metadata.
    - Avoids implicit nondeterminism: if `created_at` is not provided, the
      epoch is used to keep the record reproducible.
    """
    timestamp = created_at or datetime.fromtimestamp(0, tz=timezone.utc)
    normalized_text = canonicalize_text(raw_text)
    tokens = _tokenize(normalized_text)
    merged_metadata: Dict[str, Any] = {
        "source": source,
        "created_at": timestamp.isoformat(),
        "normalization_version": NORMALIZATION_VERSION,
    }
    if metadata:
        merged_metadata.update(metadata)
    normalized_repr = _normalized_representation(normalized_text, tokens, merged_metadata)
    meaning_hash = compute_meaning_hash(normalized_repr)
    artifact_id = sha256(normalized_text.encode("utf-8")).hexdigest()
    return CanonicalArtifact(
        artifact_id=artifact_id,
        raw_text=raw_text,
        normalized_text=normalized_text,
        tokens=tokens,
        meaning_hash=meaning_hash,
        metadata=merged_metadata,
    )
