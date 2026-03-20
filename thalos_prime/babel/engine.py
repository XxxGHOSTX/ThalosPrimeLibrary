"""Deterministic Library of Babel page engine.

This module centralizes the canonical Babel alphabet and provides reversible
index/text conversion helpers plus a storage-free deterministic page generator.
The implementation is intentionally pure and side-effect free so identical
inputs always yield identical outputs.

``ALPHABET`` is sourced from the same ordering used by
:class:`thalos_prime.lob_babel_generator.BabelGenerator` (``" .,a-z"``) so
that index/page conversions are interoperable across all Babel helpers in the
package.
"""

from __future__ import annotations

import hashlib
from typing import Final

# Canonical 29-character Babel alphabet: space, period, comma, then a-z.
# Ordering matches BabelGenerator.CHARSET so that base-29 index conversions
# are interoperable across the entire package.
ALPHABET: Final[str] = " .,abcdefghijklmnopqrstuvwxyz"
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

    Each character position is derived independently from
    ``SHA-256(seed_bytes || position_bytes)`` so the full *length* of the
    page is entropy-backed and uniformly mapped to :data:`ALPHABET`.  This
    counter-mode construction mirrors the per-position approach used by
    :class:`thalos_prime.lob_babel_generator.BabelGenerator` and avoids the
    leading-padding collapse that a single 256-bit digest would produce for
    pages longer than ~53 base-29 digits.

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

    seed_bytes = seed.encode("utf-8")
    base = len(ALPHABET)
    chars: list[str] = []
    for position in range(length):
        # Encode position as a big-endian 4-byte integer, supporting pages up to
        # 2**32 characters (well beyond the 3200-character canonical page length).
        position_bytes = position.to_bytes(4, byteorder="big")
        digest = hashlib.sha256(seed_bytes + position_bytes).digest()
        # Take the first 4 bytes (32 bits) of the digest.  4 bytes gives
        # ~4 billion distinct values; modulo 29 distributes uniformly since
        # 2**32 % 29 is small relative to 2**32.
        hash_int = int.from_bytes(digest[:4], byteorder="big")
        chars.append(ALPHABET[hash_int % base])
    return "".join(chars)
