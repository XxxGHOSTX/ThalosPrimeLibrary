"""Text reconstruction pipeline — cleans noise and segments words into artifacts."""

from __future__ import annotations

import unicodedata

from thalos_prime.library.constraints import validate_artifact
from thalos_prime.library.models import LibraryArtifact
from thalos_prime.library.store import LocalLibraryStore


def clean_noise(text: str) -> str:
    """Remove non-printable characters and normalize whitespace.

    Strips characters whose Unicode category starts with ``"C"``
    (control characters, surrogates, etc.), then collapses all
    whitespace sequences to a single space and strips leading/trailing
    whitespace.

    Args:
        text: Raw input text that may contain noise characters.

    Returns:
        Cleaned text with only printable characters and normalized spaces.

    """
    cleaned_chars = [
        ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in (" ", "\t", "\n")
    ]
    cleaned = "".join(cleaned_chars)
    return " ".join(cleaned.split())


def segment_words(text: str, min_len: int = 2) -> list[str]:
    """Split text into words, filtering those shorter than min_len.

    Args:
        text: Input text to segment.
        min_len: Minimum word length to include (default 2).

    Returns:
        List of words with length >= min_len, in order of appearance.

    """
    return [w for w in text.split() if len(w) >= min_len]


def reconstruct(
    text: str,
    store: LocalLibraryStore | None = None,
) -> list[LibraryArtifact]:
    """Deterministic text reconstruction pipeline.

    Steps:
    1. ``clean_noise(text)`` — remove non-printable characters.
    2. ``segment_words(cleaned, min_len=2)`` — filter short tokens.
    3. Reconstruct candidate content as ``" ".join(valid_words)``.
    4. Create a LibraryArtifact from the candidate content.
    5. Validate with ``validate_artifact()``.
    6. If valid and a store is provided, save to the store (dedup by id).
    7. Return a list of candidate artifacts (one artifact per call).

    Args:
        text: Input text to reconstruct.
        store: Optional LocalLibraryStore to persist valid artifacts.

    Returns:
        List containing one LibraryArtifact if reconstruction succeeds,
        or an empty list if no valid artifact could be produced.

    """
    cleaned = clean_noise(text)
    valid_words = segment_words(cleaned, min_len=2)
    if not valid_words:
        return []

    candidate_content = " ".join(valid_words)
    artifact = LibraryArtifact.create(
        content=candidate_content,
        artifact_type="text",
        metadata={"source": "reconstruct", "original_length": len(text)},
    )

    valid, _reason = validate_artifact(artifact)
    if not valid:
        return []

    if store is not None:
        store.save(artifact)

    return [artifact]


__all__ = ["clean_noise", "reconstruct", "segment_words"]
