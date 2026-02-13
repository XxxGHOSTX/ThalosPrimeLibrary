"""
Integration test for Phase 1 & 2 features

This test verifies the complete pipeline from query to scored pages.
"""

import pytest
from thalos_prime import (
    # Generator
    BabelGenerator,
    address_to_page,
    text_to_address,
    
    # Enumerator
    BabelEnumerator,
    enumerate_addresses,
    query_to_addresses,
    
    # Decoder
    BabelDecoder,
    score_coherence,
    decode_page
)


def test_full_pipeline() -> None:
    """Test complete pipeline: query → addresses → pages → scoring"""
    query = "test query"
    
    # Step 1: Enumerate addresses
    addresses = enumerate_addresses(query, max_results=3)
    assert len(addresses) > 0
    assert len(addresses) <= 3
    
    # Step 2: Generate pages
    pages = []
    for addr_info in addresses:
        page = address_to_page(addr_info['address'])
        assert len(page) == 3200
        pages.append((addr_info['address'], page))
    
    # Step 3: Score and decode
    decoded_pages = []
    for address, page in pages:
        decoded = decode_page(address, page, query=query, source='local')
        assert decoded.address == address
        assert decoded.raw_text == page
        assert decoded.source == 'local'
        assert decoded.coherence.overall_score >= 0
        assert decoded.coherence.overall_score <= 100
        decoded_pages.append(decoded)
    
    # All pages should be decoded
    assert len(decoded_pages) == len(pages)


def test_generator_enumerator_integration() -> None:
    """Test that generator can create pages for enumerated addresses"""
    enum = BabelEnumerator()
    gen = BabelGenerator()
    
    query = "hello world"
    
    # Get addresses
    results = enum.enumerate_addresses(query, max_results=5)
    
    # Generate pages for all addresses
    for result in results:
        address = result['address']
        page = gen.address_to_page(address)
        
        # Verify page is valid
        is_valid, error = gen.validate_page(page)
        assert is_valid, f"Invalid page: {error}"


def test_enumerator_decoder_integration() -> None:
    """Test that decoder can score pages from enumerated addresses"""
    enum = BabelEnumerator()
    gen = BabelGenerator()
    decoder = BabelDecoder()
    
    query = "quick brown"
    
    # Enumerate and generate
    addresses = enum.enumerate_addresses(query, max_results=3)
    
    for addr_info in addresses:
        page = gen.address_to_page(addr_info['address'])
        coherence = decoder.score_coherence(page, query)
        
        # Should have valid scores
        assert 0 <= coherence.overall_score <= 100
        assert coherence.confidence_level in ['high', 'medium', 'sparse', 'minimal']


def test_determinism_across_modules() -> None:
    """Test that operations are deterministic across all modules"""
    query = "test"
    address = "abc123"
    
    # Enumeration should be deterministic
    addrs1 = enumerate_addresses(query, max_results=3)
    addrs2 = enumerate_addresses(query, max_results=3)
    assert len(addrs1) == len(addrs2)
    for a1, a2 in zip(addrs1, addrs2):
        assert a1['address'] == a2['address']
    
    # Generation should be deterministic
    page1 = address_to_page(address)
    page2 = address_to_page(address)
    assert page1 == page2
    
    # Scoring should be deterministic
    text = "the quick brown fox"
    score1 = score_coherence(text, query)
    score2 = score_coherence(text, query)
    assert score1.overall_score == score2.overall_score


def test_package_imports() -> None:
    """Test that all main components are importable from package"""
    import thalos_prime
    
    # Check exports
    assert hasattr(thalos_prime, 'BabelGenerator')
    assert hasattr(thalos_prime, 'BabelEnumerator')
    assert hasattr(thalos_prime, 'BabelDecoder')
    assert hasattr(thalos_prime, 'address_to_page')
    assert hasattr(thalos_prime, 'enumerate_addresses')
    assert hasattr(thalos_prime, 'score_coherence')
    assert hasattr(thalos_prime, 'decode_page')


def test_query_to_pages_workflow() -> None:
    """Test a realistic query-to-pages workflow"""
    # User query
    query = "meaning of life"
    
    # Get candidate addresses
    addresses = query_to_addresses(query, count=5)
    assert len(addresses) <= 5
    
    # Generate pages
    gen = BabelGenerator()
    pages = [gen.address_to_page(addr) for addr in addresses]
    
    # Score all pages
    decoder = BabelDecoder()
    scores = []
    for page in pages:
        coherence = decoder.score_coherence(page, query)
        scores.append(coherence.overall_score)
    
    # Should have scores for all pages
    assert len(scores) == len(pages)
    
    # All scores should be in valid range
    for score in scores:
        assert 0 <= score <= 100


def test_provenance_tracking() -> None:
    """Test that provenance is correctly tracked through pipeline"""
    query = "test"
    address = "prov123"
    text = "test text with some words"
    
    # Decode with provenance
    decoded = decode_page(address, text, query=query, source='local')
    
    # Check provenance
    assert decoded.provenance['address'] == address
    assert decoded.provenance['source'] == 'local'
    assert decoded.provenance['query'] == query
    assert 'timestamp' in decoded.provenance
    assert isinstance(decoded.provenance['timestamp'], float)


def test_confidence_levels_correlation() -> None:
    """Test that confidence levels correlate with score ranges"""
    decoder = BabelDecoder()
    
    # High coherence text
    high_text = " ".join(["the quick brown fox jumps over"] * 50)
    high_score = decoder.score_coherence(high_text, query="quick")
    
    # Low coherence text
    low_text = " ".join(["xyz qwp mno"] * 50)
    low_score = decoder.score_coherence(low_text)
    
    # High should score better than low
    assert high_score.overall_score > low_score.overall_score
    
    # Confidence levels should reflect scores
    if high_score.overall_score >= 60:
        assert high_score.confidence_level in ['medium', 'high']
    if low_score.overall_score < 40:
        assert low_score.confidence_level in ['minimal', 'sparse']


def test_performance_reasonable() -> None:
    """Test that operations complete in reasonable time"""
    import time
    
    # Generate page (should be fast)
    start = time.time()
    page = address_to_page("perf_test")
    gen_time = time.time() - start
    assert gen_time < 0.1  # Should be < 100ms
    
    # Enumerate addresses (should be fast)
    start = time.time()
    addresses = enumerate_addresses("performance test", max_results=10)
    enum_time = time.time() - start
    assert enum_time < 0.1  # Should be < 100ms
    assert len(addresses) > 0
    
    # Score coherence (should be fast)
    start = time.time()
    score = score_coherence(page)
    score_time = time.time() - start
    assert score_time < 0.1  # Should be < 100ms
    assert 0.0 <= score.overall_score <= 100.0
