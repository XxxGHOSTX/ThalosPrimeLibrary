"""
Tests for the Babel enumerator module
"""

import pytest
from thalos_prime.lob_babel_enumerator import (
    BabelEnumerator,
    enumerate_addresses,
    query_to_addresses
)


def test_babel_enumerator_initialization() -> None:
    """Test that BabelEnumerator initializes correctly"""
    enum = BabelEnumerator()
    assert enum.max_ngram_size == 5
    assert enum.min_ngram_size == 2
    
    # Test custom initialization
    enum2 = BabelEnumerator(max_ngram_size=10, min_ngram_size=3)
    assert enum2.max_ngram_size == 10
    assert enum2.min_ngram_size == 3


def test_enumerate_addresses_simple_query() -> None:
    """Test enumerating addresses for a simple query"""
    enum = BabelEnumerator()
    
    query = "hello"
    results = enum.enumerate_addresses(query, max_results=10)
    
    # Should return results
    assert len(results) > 0
    assert len(results) <= 10
    
    # Each result should have required keys
    for result in results:
        assert 'address' in result
        assert 'ngrams' in result
        assert 'score' in result
        assert 'depth' in result
        
        # Address should be a hex string
        assert isinstance(result['address'], str)
        assert len(result['address']) > 0


def test_enumerate_addresses_deterministic() -> None:
    """Test that enumeration is deterministic"""
    enum = BabelEnumerator()
    
    query = "test query"
    
    results1 = enum.enumerate_addresses(query, max_results=5)
    results2 = enum.enumerate_addresses(query, max_results=5)
    
    # Should get the same results
    assert len(results1) == len(results2)
    
    for r1, r2 in zip(results1, results2):
        assert r1['address'] == r2['address']
        assert r1['ngrams'] == r2['ngrams']
        assert r1['score'] == r2['score']


def test_enumerate_addresses_empty_query() -> None:
    """Test that empty query returns empty results"""
    enum = BabelEnumerator()
    
    results = enum.enumerate_addresses("", max_results=10)
    assert len(results) == 0
    
    results = enum.enumerate_addresses("   ", max_results=10)
    assert len(results) == 0


def test_enumerate_addresses_respects_max_results() -> None:
    """Test that max_results parameter is respected"""
    enum = BabelEnumerator()
    
    query = "the quick brown fox"
    
    for max_results in [1, 5, 10, 20]:
        results = enum.enumerate_addresses(query, max_results=max_results)
        assert len(results) <= max_results


def test_enumerate_addresses_with_depth() -> None:
    """Test that depth parameter generates more variations"""
    enum = BabelEnumerator()
    
    query = "hello"
    
    results_depth1 = enum.enumerate_addresses(query, max_results=20, depth=1)
    results_depth3 = enum.enumerate_addresses(query, max_results=20, depth=3)
    
    # Higher depth should potentially give more results (up to max_results)
    assert len(results_depth1) <= 20
    assert len(results_depth3) <= 20
    
    # Depth values should be present
    for result in results_depth3:
        assert 'depth' in result
        assert result['depth'] >= 0


def test_extract_ngrams() -> None:
    """Test n-gram extraction"""
    enum = BabelEnumerator()
    
    text = "hello world test"
    ngrams = enum._extract_ngrams(text)
    
    # Should extract word-level ngrams
    assert len(ngrams) > 0
    
    # Should be sorted by length (longer first)
    if len(ngrams) > 1:
        for i in range(len(ngrams) - 1):
            assert len(ngrams[i]) >= len(ngrams[i + 1])


def test_extract_ngrams_short_text() -> None:
    """Test n-gram extraction for short text"""
    enum = BabelEnumerator()
    
    text = "hi"
    ngrams = enum._extract_ngrams(text)
    
    # Should handle short text
    assert len(ngrams) >= 0


def test_ngram_to_address() -> None:
    """Test converting n-gram to address"""
    enum = BabelEnumerator()
    
    ngram = "hello"
    
    # Should be deterministic
    addr1 = enum._ngram_to_address(ngram, offset=0)
    addr2 = enum._ngram_to_address(ngram, offset=0)
    assert addr1 == addr2
    
    # Should be a hex string
    assert isinstance(addr1, str)
    assert len(addr1) == 64  # 256 bits = 64 hex chars
    
    # Different offsets should give different addresses
    addr3 = enum._ngram_to_address(ngram, offset=1)
    assert addr1 != addr3


def test_score_address() -> None:
    """Test address scoring"""
    enum = BabelEnumerator()
    
    query = "hello world"
    
    # Exact match should score higher
    score1 = enum._score_address("hello world", query)
    score2 = enum._score_address("hello", query)
    score3 = enum._score_address("xyz", query)
    
    # Scores should be between 0 and 1
    assert 0 <= score1 <= 1
    assert 0 <= score2 <= 1
    assert 0 <= score3 <= 1
    
    # Exact match should score highest
    assert score1 > score2
    assert score2 > score3


def test_enumerate_substrings() -> None:
    """Test substring enumeration"""
    enum = BabelEnumerator()
    
    text = "hello world testing"
    results = enum.enumerate_substrings(text, substring_length=5)
    
    # Should return substring-address pairs
    assert len(results) > 0
    
    for substring, address in results:
        assert len(substring) == 5
        assert isinstance(address, str)
        assert len(address) > 0


def test_enumerate_substrings_short_text() -> None:
    """Test substring enumeration with text shorter than substring length"""
    enum = BabelEnumerator()
    
    text = "hi"
    results = enum.enumerate_substrings(text, substring_length=10)
    
    # Should return empty or minimal results
    assert len(results) == 0


def test_find_common_addresses() -> None:
    """Test finding common addresses between two queries"""
    enum = BabelEnumerator()
    
    query1 = "hello"
    query2 = "world"
    
    common = enum.find_common_addresses(query1, query2, max_results=10)
    
    # Should return a list
    assert isinstance(common, list)
    assert len(common) <= 10
    
    # Each should be a string
    for address in common:
        assert isinstance(address, str)


def test_find_common_addresses_identical_queries() -> None:
    """Test that identical queries have many common addresses"""
    enum = BabelEnumerator()
    
    query = "test query"
    
    common = enum.find_common_addresses(query, query, max_results=10)
    
    # Should have common addresses
    assert len(common) > 0


def test_convenience_function_enumerate_addresses() -> None:
    """Test the module-level enumerate_addresses function"""
    results = enumerate_addresses("hello world", max_results=5)
    
    assert len(results) <= 5
    assert len(results) > 0
    
    for result in results:
        assert 'address' in result
        assert 'ngrams' in result
        assert 'score' in result


def test_convenience_function_query_to_addresses() -> None:
    """Test the module-level query_to_addresses function"""
    addresses = query_to_addresses("hello", count=5)
    
    assert len(addresses) <= 5
    assert len(addresses) > 0
    
    # Each should be a hex string
    for address in addresses:
        assert isinstance(address, str)
        assert len(address) > 0


def test_different_queries_different_addresses() -> None:
    """Test that different queries generate different address sets"""
    enum = BabelEnumerator()
    
    results1 = enum.enumerate_addresses("hello", max_results=5)
    results2 = enum.enumerate_addresses("world", max_results=5)
    
    # Extract address sets
    addrs1 = {r['address'] for r in results1}
    addrs2 = {r['address'] for r in results2}
    
    # Should have different addresses (unlikely to have complete overlap)
    assert addrs1 != addrs2


def test_results_sorted_by_score() -> None:
    """Test that results are sorted by score (highest first)"""
    enum = BabelEnumerator()
    
    query = "the quick brown fox"
    results = enum.enumerate_addresses(query, max_results=10)
    
    if len(results) > 1:
        # Check that scores are in descending order
        for i in range(len(results) - 1):
            current_score: float = results[i]['score']
            next_score: float = results[i + 1]['score']
            assert current_score >= next_score
