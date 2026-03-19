"""Deterministic Library of Babel page engine.

This module centralizes the canonical Babel alphabet and provides reversible
index/text conversion helpers plus a storage-free deterministic page generator.
The implementation is intentionally pure and side-effect free so identical
inputs always yield identical outputs.
"""

from __future__ import annotations

import hashlib
import string
from typing import Final

ALPHABET: Final[str] = string.ascii_lowercase + " .,"
DEFAULT_PAGE_LENGTH: Final[int] = 3200


def basile_index_to_text(index: int, length: int) -> str:
    """Convert a non-negative integer into deterministic Babel text.

    Args:
        index: Integer address in the Babel alphabet space.
        length: Number of characters to render.

    Returns:
        A fixed-length text composed only of :data:`ALPHABET`.

    Raises:
        ValueError: If *index* is negative or *length* is negative.
    """
    if index < 0:
        raise ValueError("index must be non-negative")
    if length < 0:
        raise ValueError("length must be non-negative")

    base = len(ALPHABET)
    chars: list[str] = []
    remaining = index
    for _ in range(length):
        remaining, rem = divmod(remaining, base)
        chars.append(ALPHABET[rem])
    return "".join(reversed(chars))



def text_to_basile_index(text: str) -> int:
    """Convert Babel text into its integer representation.

    Args:
        text: Text composed exclusively of :data:`ALPHABET`.

    Returns:
        Integer address for the supplied text.

    Raises:
        ValueError: If *text* contains characters outside the Babel alphabet.
    """
    base = len(ALPHABET)
    index = 0
    for char in text:
        try:
            digit = ALPHABET.index(char)
        except ValueError as exc:
            raise ValueError(f"unsupported Babel character: {char!r}") from exc
        index = index * base + digit
    return index



def deterministic_page(seed: str, length: int = DEFAULT_PAGE_LENGTH) -> str:
    """Generate a deterministic Babel page from *seed*.

    The page is derived entirely from the SHA-256 digest of *seed*, so the
    generation is fully procedural and requires no persistent storage.

    Args:
        seed: Seed material used to derive the page.
        length: Desired page length.

    Returns:
        Deterministic Babel page text.

    Raises:
        ValueError: If *length* is negative.
    """
    if length < 0:
        raise ValueError("length must be non-negative")

    hash_val = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)
    return basile_index_to_text(hash_val, length)
