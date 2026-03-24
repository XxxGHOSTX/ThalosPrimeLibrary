"""Constraint validation functions for library artifacts."""

from __future__ import annotations

from thalos_prime.library.models import LibraryArtifact


def validate_min_word_length(content: str, min_len: int = 2) -> bool:
    """Return True if all whitespace-split words have length >= min_len.

    An empty content string is considered valid (no words to violate).

    Args:
        content: Text to validate.
        min_len: Minimum acceptable word length (default 2).

    Returns:
        True if all words meet the minimum length requirement.

    """
    words = content.split()
    if not words:
        return True
    return all(len(w) >= min_len for w in words)


def validate_artifact(artifact: LibraryArtifact) -> tuple[bool, str]:
    """Validate a library artifact against content constraints.

    Checks:
    - Content must not be empty.
    - All whitespace-split words must have length >= 2.

    Args:
        artifact: LibraryArtifact to validate.

    Returns:
        Tuple of ``(valid, reason)`` where ``valid`` is True on success and
        ``reason`` describes the first violated constraint on failure.

    """
    if not artifact.content.strip():
        return False, "Content is empty"
    if not validate_min_word_length(artifact.content, min_len=2):
        return False, "Content contains words shorter than 2 characters"
    return True, "ok"


__all__ = ["validate_artifact", "validate_min_word_length"]
