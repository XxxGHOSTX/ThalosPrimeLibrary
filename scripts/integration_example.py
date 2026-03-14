"""
Integration example demonstrating Phase 1 & 2 features

This example shows how to:
1. Generate deterministic pages from addresses
2. Enumerate addresses from queries
3. Score coherence of generated pages
4. Decode pages with full provenance

Usage:
    python integration_example.py
"""

from thalos_prime.lob_babel_generator import BabelGenerator, address_to_page
from thalos_prime.lob_babel_enumerator import BabelEnumerator, enumerate_addresses
from thalos_prime.lob_decoder import BabelDecoder, decode_page


def demo_generator():
    """Demonstrate the deterministic generator"""
    print("=" * 70)
    print("DEMO 1: Deterministic Page Generation")
    print("=" * 70)
    
    gen = BabelGenerator()
    
    # Generate a page from a hex address
    address = "abc123def456"
    page = gen.address_to_page(address)
    
    print(f"\nAddress: {address}")
    print(f"Page length: {len(page)} characters")
    print(f"First 100 characters: {page[:100]}")
    
    # Verify determinism
    page2 = gen.address_to_page(address)
    print(f"\nDeterministic: {page == page2}")
    
    # Generate from different addresses
    addresses = ["000", "111", "aaa", "fff"]
    print("\nFirst 50 chars from different addresses:")
    for addr in addresses:
        p = gen.address_to_page(addr)
        print(f"  {addr}: {p[:50]}")
    
    print()


def demo_enumerator():
    """Demonstrate the query enumerator"""
    print("=" * 70)
    print("DEMO 2: Query to Address Enumeration")
    print("=" * 70)
    
    enum = BabelEnumerator()
    
    # Enumerate addresses for a query
    query = "hello world"
    results = enum.enumerate_addresses(query, max_results=5)
    
    print(f"\nQuery: '{query}'")
    print(f"Generated {len(results)} candidate addresses:\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. Address: {result['address'][:40]}...")
        print(f"   N-grams: {result['ngrams']}")
        print(f"   Score: {result['score']:.3f}")
        print(f"   Depth: {result['depth']}")
        print()


def demo_decoder():
    """Demonstrate coherence scoring and decoding"""
    print("=" * 70)
    print("DEMO 3: Coherence Scoring")
    print("=" * 70)
    
    decoder = BabelDecoder()
    
    # Test with different types of text
    texts = [
        ("High coherence", "the quick brown fox jumps over the lazy dog. this is a test sentence."),
        ("Medium coherence", "hello world test example with some common words and structure."),
        ("Low coherence", "xyz abc qwp random letters without much meaning or structure here")
    ]
    
    for label, text in texts:
        coherence = decoder.score_coherence(text, query="quick brown")
        
        print(f"\n{label}:")
        print(f"  Text: {text[:60]}...")
        print(f"  Overall score: {coherence.overall_score:.2f}/100")
        print(f"  Language score: {coherence.language_score:.2f}/100")
        print(f"  Structure score: {coherence.structure_score:.2f}/100")
        print(f"  N-gram score: {coherence.ngram_score:.2f}/100")
        print(f"  Exact match score: {coherence.exact_match_score:.2f}/100")
        print(f"  Confidence: {coherence.confidence_level}")
    
    print()


def demo_full_pipeline():
    """Demonstrate the full pipeline: query → addresses → pages → scoring"""
    print("=" * 70)
    print("DEMO 4: Full Pipeline Integration")
    print("=" * 70)
    
    query = "test query"
    print(f"\nQuery: '{query}'")
    print("-" * 70)
    
    # Step 1: Enumerate addresses
    enum = BabelEnumerator()
    addresses = enumerate_addresses(query, max_results=3)
    
    print(f"\nStep 1: Enumerated {len(addresses)} addresses")
    
    # Step 2: Generate pages
    gen = BabelGenerator()
    pages = []
    
    print("\nStep 2: Generated pages from addresses")
    for addr_info in addresses:
        address = addr_info['address']
        page = gen.address_to_page(address)
        pages.append((address, page))
        print(f"  - Address {address[:20]}...: {len(page)} chars")
    
    # Step 3: Score and decode
    decoder = BabelDecoder()
    
    print("\nStep 3: Scored and decoded pages:")
    decoded_pages = []
    
    for address, page in pages:
        decoded = decoder.decode_page(
            address=address,
            text=page,
            query=query,
            source='local'
        )
        decoded_pages.append(decoded)
        
        print(f"\n  Address: {address[:30]}...")
        print(f"  Coherence: {decoded.coherence.overall_score:.2f}/100 ({decoded.coherence.confidence_level})")
        print(f"  Language: {decoded.coherence.language_score:.2f}/100")
        print(f"  Structure: {decoded.coherence.structure_score:.2f}/100")
        print(f"  Source: {decoded.source}")
        print(f"  Provenance recorded: {bool(decoded.provenance)}")
    
    # Sort by score
    decoded_pages.sort(key=lambda x: x.coherence.overall_score, reverse=True)
    
    print("\n" + "=" * 70)
    print(f"Best result: Score {decoded_pages[0].coherence.overall_score:.2f}/100")
    print(f"Address: {decoded_pages[0].address[:40]}...")
    print(f"Preview: {decoded_pages[0].raw_text[:100]}...")
    print("=" * 70)


def demo_text_to_address():
    """Demonstrate text to address conversion"""
    print("=" * 70)
    print("DEMO 5: Text to Address (Reverse Lookup)")
    print("=" * 70)
    
    gen = BabelGenerator()
    
    text = "hello world this is a test"
    address = gen.text_to_address(text)
    
    print(f"\nText: '{text}'")
    print(f"Address: {address[:60]}...")
    
    # Verify it's deterministic
    address2 = gen.text_to_address(text)
    print(f"\nDeterministic: {address == address2}")
    
    # Different texts give different addresses
    texts = ["hello", "world", "test"]
    print("\nDifferent texts → different addresses:")
    for t in texts:
        addr = gen.text_to_address(t)
        print(f"  '{t}' → {addr[:40]}...")
    
    print()


def main():
    """Run all demonstrations"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  THALOS PRIME - Phase 1 & 2 Integration Demo".center(68) + "║")
    print("║" + "  Deterministic Generation + Enhanced Coherence Scoring".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    try:
        demo_generator()
        input("Press Enter to continue to next demo...")
        
        demo_enumerator()
        input("Press Enter to continue to next demo...")
        
        demo_decoder()
        input("Press Enter to continue to next demo...")
        
        demo_text_to_address()
        input("Press Enter to continue to full pipeline demo...")
        
        demo_full_pipeline()
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    
    print("\n" + "=" * 70)
    print("Demo complete! All Phase 1 & 2 features demonstrated.")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
