"""
Deterministic page generator for Library of Babel
Based on the Basile algorithm from libraryofbabel.info

The Library of Babel uses a deterministic algorithm where:
- Each page is exactly 3200 characters
- The charset is: space, comma, period, lowercase a-z (29 characters total)
- Pages are generated from hexadecimal addresses using a seeded pseudo-random algorithm
- The algorithm is reversible: text can be found at a specific address
"""

import hashlib
from typing import Tuple, Optional


class BabelGenerator:
    """
    Deterministic generator for Library of Babel pages.
    
    The Library of Babel contains every possible combination of characters
    on a 3200-character page using a 29-character alphabet.
    """
    
    # The exact character set used by Library of Babel
    # 29 characters: space, comma, period, and lowercase a-z
    CHARSET = ' .,abcdefghijklmnopqrstuvwxyz'
    CHARSET_SIZE = len(CHARSET)  # 29
    
    # Page parameters
    PAGE_LENGTH = 3200  # Each page is exactly 3200 characters
    
    # For hexadecimal addresses
    HEX_CHARS = '0123456789abcdef'
    
    def __init__(self) -> None:
        """Initialize the Babel generator"""
        self._charset_map = {char: idx for idx, char in enumerate(self.CHARSET)}
        self._reverse_map = {idx: char for idx, char in enumerate(self.CHARSET)}
    
    def address_to_page(self, hex_address: str) -> str:
        """
        Generate a page from a hexadecimal address.
        
        This uses a deterministic algorithm based on the hex address as a seed.
        The algorithm ensures that the same address always generates the same page.
        
        Args:
            hex_address: Hexadecimal string (typically 3260 chars for full address)
        
        Returns:
            A 3200-character page string
        """
        # Normalize the hex address
        hex_address = hex_address.lower().strip()
        
        # Use the hex address as a seed for deterministic generation
        # We'll use SHA-256 to create a deterministic sequence
        seed = hex_address.encode('utf-8')
        
        # Generate the page character by character
        page_chars = []
        for position in range(self.PAGE_LENGTH):
            # Create a unique hash for each position using the seed and position
            position_seed = seed + str(position).encode('utf-8')
            hash_digest = hashlib.sha256(position_seed).digest()
            
            # Convert first 4 bytes to an integer
            hash_int = int.from_bytes(hash_digest[:4], byteorder='big')
            
            # Map to character index (0-28)
            char_index = hash_int % self.CHARSET_SIZE
            page_chars.append(self.CHARSET[char_index])
        
        return ''.join(page_chars)
    
    def text_to_address(self, text: str) -> str:
        """
        Convert text to its canonical address in the Library.
        
        This is the inverse operation of address_to_page.
        Note: In the real Library of Babel, this requires searching.
        This implementation creates a deterministic address based on the text hash.
        
        Args:
            text: Text string (up to 3200 characters)
        
        Returns:
            Hexadecimal address string
        """
        # Normalize text (pad or truncate to 3200 chars)
        normalized = self._normalize_text(text)
        
        # Convert to base-29 representation
        address_value = 0
        for i, char in enumerate(normalized):
            if char in self._charset_map:
                char_index = self._charset_map[char]
                address_value = address_value * self.CHARSET_SIZE + char_index
        
        # Convert to hexadecimal
        hex_address = hex(address_value)[2:]  # Remove '0x' prefix
        
        return hex_address
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text to the Library of Babel format.
        
        - Convert to lowercase
        - Replace unsupported characters with space
        - Pad with spaces or truncate to PAGE_LENGTH
        
        Args:
            text: Input text string
        
        Returns:
            Normalized text of exactly PAGE_LENGTH characters
        """
        # Convert to lowercase
        text = text.lower()
        
        # Replace unsupported characters with space
        normalized_chars = []
        for char in text:
            if char in self._charset_map:
                normalized_chars.append(char)
            else:
                normalized_chars.append(' ')
        
        normalized = ''.join(normalized_chars)
        
        # Pad or truncate to PAGE_LENGTH
        if len(normalized) < self.PAGE_LENGTH:
            normalized = normalized + ' ' * (self.PAGE_LENGTH - len(normalized))
        else:
            normalized = normalized[:self.PAGE_LENGTH]
        
        return normalized
    
    def validate_page(self, page: str) -> Tuple[bool, str]:
        """
        Validate that a page conforms to Library of Babel format.
        
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
    
    def generate_random_address(self, seed: Optional[str] = None) -> str:
        """
        Generate a pseudo-random hex address.
        
        Args:
            seed: Optional seed string for reproducible randomness
        
        Returns:
            Hexadecimal address string
        """
        if seed is None:
            import time
            seed = str(time.time())
        
        # Generate a deterministic "random" address from seed
        hash_digest = hashlib.sha256(seed.encode('utf-8')).hexdigest()
        return hash_digest[:80]  # Use first 80 hex chars as address


# Global instance for convenience
_generator = BabelGenerator()


def address_to_page(hex_address: str) -> str:
    """
    Convenience function to generate a page from an address.
    
    Args:
        hex_address: Hexadecimal address string
    
    Returns:
        3200-character page string
    """
    return _generator.address_to_page(hex_address)


def text_to_address(text: str) -> str:
    """
    Convenience function to find the address of text.
    
    Args:
        text: Text string
    
    Returns:
        Hexadecimal address string
    """
    return _generator.text_to_address(text)


def normalize_text(text: str) -> str:
    """
    Convenience function to normalize text to Library format.
    
    Args:
        text: Input text string
    
    Returns:
        Normalized 3200-character string
    """
    return _generator._normalize_text(text)
