"""
Tests for the Babel generator module
"""

import pytest
from thalos_prime.lob_babel_generator import (
    BabelGenerator,
    address_to_page,
    text_to_address,
    normalize_text
)


def test_babel_generator_initialization():
    """Test that BabelGenerator initializes correctly"""
    gen = BabelGenerator()
    assert gen.CHARSET_SIZE == 29
    assert gen.PAGE_LENGTH == 3200
    assert len(gen.CHARSET) == 29


def test_charset_contents():
    """Test that the charset contains expected characters"""
    gen = BabelGenerator()
    # Should have space, comma, period, and a-z
    assert ' ' in gen.CHARSET
    assert ',' in gen.CHARSET
    assert '.' in gen.CHARSET
    assert 'a' in gen.CHARSET
    assert 'z' in gen.CHARSET
    assert 'A' not in gen.CHARSET  # Only lowercase


def test_address_to_page_deterministic():
    """Test that the same address always generates the same page"""
    gen = BabelGenerator()
    address = "abc123def456"
    
    page1 = gen.address_to_page(address)
    page2 = gen.address_to_page(address)
    page3 = gen.address_to_page(address)
    
    assert page1 == page2 == page3
    assert len(page1) == 3200


def test_address_to_page_length():
    """Test that generated pages are exactly 3200 characters"""
    gen = BabelGenerator()
    
    test_addresses = [
        "0",
        "abc",
        "123456789abcdef",
        "f" * 100,
        "a1b2c3d4e5f6"
    ]
    
    for address in test_addresses:
        page = gen.address_to_page(address)
        assert len(page) == 3200, f"Page from {address} has wrong length: {len(page)}"


def test_address_to_page_valid_characters():
    """Test that generated pages only contain valid characters"""
    gen = BabelGenerator()
    address = "test123"
    
    page = gen.address_to_page(address)
    
    for char in page:
        assert char in gen.CHARSET, f"Invalid character '{char}' in generated page"


def test_different_addresses_different_pages():
    """Test that different addresses generate different pages"""
    gen = BabelGenerator()
    
    page1 = gen.address_to_page("address1")
    page2 = gen.address_to_page("address2")
    page3 = gen.address_to_page("address3")
    
    # Should be different (extremely unlikely to collide)
    assert page1 != page2
    assert page2 != page3
    assert page1 != page3


def test_normalize_text_length():
    """Test that normalized text is exactly 3200 characters"""
    gen = BabelGenerator()
    
    # Short text should be padded
    short = "hello"
    normalized = gen._normalize_text(short)
    assert len(normalized) == 3200
    
    # Long text should be truncated
    long = "a" * 5000
    normalized = gen._normalize_text(long)
    assert len(normalized) == 3200


def test_normalize_text_lowercase():
    """Test that text is converted to lowercase"""
    gen = BabelGenerator()
    
    text = "HELLO WORLD"
    normalized = gen._normalize_text(text)
    assert "HELLO" not in normalized
    assert "hello" in normalized


def test_normalize_text_invalid_characters():
    """Test that invalid characters are replaced with space"""
    gen = BabelGenerator()
    
    text = "hello@world#123!"
    normalized = gen._normalize_text(text)
    
    # Should not contain invalid characters
    assert '@' not in normalized
    assert '#' not in normalized
    assert '!' not in normalized
    
    # Should contain the valid characters
    assert 'h' in normalized
    assert 'e' in normalized


def test_validate_page_valid():
    """Test validation of a valid page"""
    gen = BabelGenerator()
    
    # Generate a valid page
    page = gen.address_to_page("test")
    is_valid, error = gen.validate_page(page)
    
    assert is_valid
    assert error == ""


def test_validate_page_wrong_length():
    """Test validation catches wrong length"""
    gen = BabelGenerator()
    
    short_page = "hello world"
    is_valid, error = gen.validate_page(short_page)
    
    assert not is_valid
    assert "length" in error.lower()


def test_validate_page_invalid_character():
    """Test validation catches invalid characters"""
    gen = BabelGenerator()
    
    # Create a page with an invalid character
    invalid_page = "a" * 3199 + "@"
    is_valid, error = gen.validate_page(invalid_page)
    
    assert not is_valid
    assert "invalid character" in error.lower()


def test_text_to_address():
    """Test converting text to an address"""
    gen = BabelGenerator()
    
    text = "hello world"
    address = gen.text_to_address(text)
    
    # Should return a hex string
    assert isinstance(address, str)
    assert len(address) > 0
    
    # Should be deterministic
    address2 = gen.text_to_address(text)
    assert address == address2


def test_text_to_address_different_texts():
    """Test that different texts produce different addresses"""
    gen = BabelGenerator()
    
    addr1 = gen.text_to_address("hello")
    addr2 = gen.text_to_address("world")
    addr3 = gen.text_to_address("hello world")
    
    # Should all be different
    assert addr1 != addr2
    assert addr2 != addr3
    assert addr1 != addr3


def test_generate_random_address():
    """Test random address generation"""
    gen = BabelGenerator()
    
    # With seed, should be deterministic
    addr1 = gen.generate_random_address(seed="test")
    addr2 = gen.generate_random_address(seed="test")
    assert addr1 == addr2
    
    # Different seeds should give different addresses
    addr3 = gen.generate_random_address(seed="other")
    assert addr1 != addr3


def test_convenience_functions():
    """Test the module-level convenience functions"""
    # Test address_to_page
    page = address_to_page("test123")
    assert len(page) == 3200
    
    # Test text_to_address
    address = text_to_address("hello world")
    assert isinstance(address, str)
    
    # Test normalize_text
    normalized = normalize_text("HELLO")
    assert len(normalized) == 3200
    assert "hello" in normalized


def test_roundtrip_consistency():
    """Test that text->address->page is consistent"""
    gen = BabelGenerator()
    
    original_text = "the quick brown fox jumps over the lazy dog"
    
    # Convert text to address
    address = gen.text_to_address(original_text)
    
    # The address should be deterministic
    address2 = gen.text_to_address(original_text)
    assert address == address2
    
    # The same address should always generate the same page
    page1 = gen.address_to_page(address)
    page2 = gen.address_to_page(address)
    assert page1 == page2
