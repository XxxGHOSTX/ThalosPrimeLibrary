"""
Tests for deterministic ingestion and canonicalization.
"""

from datetime import datetime, timezone

from thalos_prime.ingest import (
    CanonicalArtifact,
    compute_meaning_hash,
    canonicalize_text,
    ingest_fragment,
)
from hashlib import sha256


def test_canonicalize_text_collapses_whitespace_and_quotes() -> None:
    """Curly quotes and whitespace are normalized deterministically."""
    raw = "  “Hello” — World\t\n"
    assert canonicalize_text(raw) == '"hello" - world'


def test_compute_meaning_hash_deterministic() -> None:
    """Meaning hash is stable for equivalent normalized representations."""
    normalized_repr = {
        "normalized_text": "alpha beta",
        "tokens": ["alpha", "beta"],
        "schema_version": "1.0.0",
        "metadata": {"source": "test", "created_at": "1970-01-01T00:00:00+00:00"},
    }
    first = compute_meaning_hash(normalized_repr)
    second = compute_meaning_hash(normalized_repr.copy())
    assert first == second


def test_ingest_fragment_builds_artifact() -> None:
    """Ingestion returns a deterministic CanonicalArtifact."""
    created = datetime(2024, 1, 1, tzinfo=timezone.utc)
    artifact: CanonicalArtifact = ingest_fragment(
        "Noise   turns  into PATTERNS",
        source="unit-test",
        created_at=created,
        metadata={"trace_id": "abc123"},
    )
    assert artifact.normalized_text == "noise turns into patterns"
    # artifact_id derives solely from normalized text
    expected_artifact_id = sha256(artifact.normalized_text.encode("utf-8")).hexdigest()
    assert artifact.artifact_id == expected_artifact_id
    assert artifact.tokens == ["noise", "turns", "into", "patterns"]
    assert artifact.metadata["source"] == "unit-test"
    assert artifact.metadata["created_at"] == created.isoformat()
    assert artifact.metadata["normalization_version"] == "1.0.0"
    assert artifact.metadata["trace_id"] == "abc123"
