"""Deterministic page generator for the Library of Babel.

Implements a Linear Congruential Generator (LCG)-based algorithm for fast,
deterministic page generation from hexadecimal addresses.  This is the
canonical page generator; the older SHA-256-per-character approach has been
removed.

Algorithm properties:
- Each page is exactly 3200 characters.
- Charset: space, comma, period, lowercase a-z (29 characters total).
- LCG constants: a=1103515245, c=12345, m=2**31 (identical to those in
  src/lob_babel_generator.py, making results reproducible across modules).
- The page is seeded from SHA-256(hex_address), so the same address always
  produces the same page and different addresses produce different pages.
"""

import hashlib

# ---------------------------------------------------------------------------
# Module-level LCG constants (matching src/lob_babel_generator.py exactly)
# ---------------------------------------------------------------------------
_LCG_A: int = 1103515245
_LCG_C: int = 12345
_LCG_M: int = 2**31


def _lcg(state: int) -> int:
    """Advance the LCG state by one step."""
    return (_LCG_A * state + _LCG_C) % _LCG_M


class BabelGenerator:
    """Deterministic generator for Library of Babel pages using LCG.

    The Library of Babel contains every possible combination of characters
    on a 3200-character page using a 29-character alphabet.
    """

    # The exact character set used by Library of Babel
    # 29 characters: space, comma, period, and lowercase a-z
    CHARSET = " .,abcdefghijklmnopqrstuvwxyz"
    CHARSET_SIZE = len(CHARSET)  # 29

    # Page parameters
    PAGE_LENGTH = 3200  # Each page is exactly 3200 characters

    # For hexadecimal addresses
    HEX_CHARS = "0123456789abcdef"

    def __init__(self) -> None:
        """Initialize the Babel generator."""
        self._charset_map = {char: idx for idx, char in enumerate(self.CHARSET)}
        self._reverse_map = dict(enumerate(self.CHARSET))

    def address_to_page(self, hex_address: str) -> str:
        """Generate a page from a hexadecimal address using the LCG algorithm.

        The address is hashed with SHA-256 to derive a 32-bit integer seed,
        then the LCG advances once per character to select from CHARSET.
        The same address always produces the same page.

        Args:
            hex_address: Hexadecimal string (any length).

        Returns:
            A 3200-character page string using the 29-character Library charset.

        """
        hex_address = hex_address.lower().strip()
        seed = self._seed_from_hex(hex_address)
        state = seed
        page_chars: list[str] = []
        for _ in range(self.PAGE_LENGTH):
            state = _lcg(state)
            page_chars.append(self.CHARSET[state % self.CHARSET_SIZE])
        return "".join(page_chars)

    @staticmethod
    def _seed_from_hex(hex_address: str) -> int:
        """Derive a deterministic 32-bit seed from a hex address string."""
        digest = hashlib.sha256(hex_address.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big")

    def text_to_address(self, text: str) -> str:
        """Convert text to its canonical address in the Library.

        This is the inverse operation of address_to_page.
        Note: In the real Library of Babel, this requires searching.
        This implementation creates a deterministic address based on the text hash.

        Args:
            text: Text string (up to 3200 characters)

        Returns:
            Hexadecimal address string

        """
        normalized = self._normalize_text(text)

        address_value = 0
        for char in normalized:
            if char in self._charset_map:
                char_index = self._charset_map[char]
                address_value = address_value * self.CHARSET_SIZE + char_index

        return f"{address_value:x}"

    def _normalize_text(self, text: str) -> str:
        """Normalize text to the Library of Babel format.

        - Convert to lowercase
        - Replace unsupported characters with space
        - Pad with spaces or truncate to PAGE_LENGTH

        Args:
            text: Input text string

        Returns:
            Normalized text of exactly PAGE_LENGTH characters

        """
        text = text.lower()

        normalized_chars = []
        for char in text:
            if char in self._charset_map:
                normalized_chars.append(char)
            else:
                normalized_chars.append(" ")

        normalized = "".join(normalized_chars)

        if len(normalized) < self.PAGE_LENGTH:
            normalized = normalized + " " * (self.PAGE_LENGTH - len(normalized))
        else:
            normalized = normalized[: self.PAGE_LENGTH]

        return normalized

    def validate_page(self, page: str) -> tuple[bool, str]:
        """Validate that a page conforms to Library of Babel format.

        Args:
            page: Page string to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        if len(page) != self.PAGE_LENGTH:
            return False, f"Page length must be {self.PAGE_LENGTH}, got {len(page)}"

        for i, char in enumerate(page):
            if char not in self._charset_map:
                return False, f"Invalid character '{char}' at position {i}"

        return True, ""

    def generate_random_address(self, seed: str | None = None) -> str:
        """Generate a deterministic hex address from an optional seed.

        When seed is None a fixed default is used so the method remains
        deterministic (non-deterministic time-based seeding has been removed).

        Args:
            seed: Optional seed string for reproducible generation.

        Returns:
            Hexadecimal address string (80 hex characters).

        """
        effective_seed = seed if seed is not None else "thalos-prime-default-seed"
        hash_digest = hashlib.sha256(effective_seed.encode("utf-8")).hexdigest()
        return hash_digest[:80]  # Use first 80 hex chars as address


# Global instance for convenience
_generator = BabelGenerator()


def address_to_page(hex_address: str) -> str:
    """Convenience function to generate a page from an address.

    Args:
        hex_address: Hexadecimal address string

    Returns:
        3200-character page string

    """
    return _generator.address_to_page(hex_address)


def text_to_address(text: str) -> str:
    """Convenience function to find the address of text.

    Args:
        text: Text string

    Returns:
        Hexadecimal address string

    """
    return _generator.text_to_address(text)


def normalize_text(text: str) -> str:
    """Convenience function to normalize text to Library format.

    Args:
        text: Input text string

    Returns:
        Normalized 3200-character string

    """
    return _generator._normalize_text(text)
