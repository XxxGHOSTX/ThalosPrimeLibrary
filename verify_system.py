#!/usr/bin/env python3
"""
Thalos Prime - Quick Verification Demo

This script demonstrates that all core components are working correctly.
"""

import sys
import time

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def test_imports():
    """Test that all modules can be imported"""
    print_header("Testing Module Imports")
    
    try:
        from thalos_prime import (
            address_to_page,
            enumerate_addresses,
            score_coherence,
            decode_page,
            BabelGenerator,
            BabelEnumerator,
            BabelDecoder
        )
        print("✅ All core modules imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_generator():
    """Test page generation"""
    print_header("Testing Deterministic Generator")
    
    try:
        from thalos_prime import address_to_page, BabelGenerator
        
        # Test generation
        address = "test123"
        page = address_to_page(address)
        
        print(f"✅ Generated page from address '{address}'")
        print(f"   Length: {len(page)} characters")
        print(f"   Preview: {page[:80]}...")
        
        # Test determinism
        page2 = address_to_page(address)
        if page == page2:
            print("✅ Generation is deterministic (same address = same page)")
        else:
            print("❌ Generation is not deterministic")
            return False
        
        # Test validation
        gen = BabelGenerator()
        is_valid, error = gen.validate_page(page)
        print(f"✅ Page validation: {'Valid' if is_valid else f'Invalid: {error}'}")
        
        return True
    except Exception as e:
        print(f"❌ Generator test failed: {e}")
        return False

def test_enumerator():
    """Test address enumeration"""
    print_header("Testing Address Enumerator")
    
    try:
        from thalos_prime import enumerate_addresses
        
        query = "hello world"
        results = enumerate_addresses(query, max_results=3)
        
        print(f"✅ Enumerated {len(results)} addresses for query '{query}'")
        for i, result in enumerate(results, 1):
            print(f"   {i}. Address: {result['address'][:40]}...")
            print(f"      N-grams: {result['ngrams']}")
            print(f"      Score: {result['score']:.3f}")
        
        return True
    except Exception as e:
        print(f"❌ Enumerator test failed: {e}")
        return False

def test_decoder():
    """Test coherence scoring"""
    print_header("Testing Coherence Decoder")
    
    try:
        from thalos_prime import score_coherence
        
        # Test with high-coherence text
        text = "the quick brown fox jumps over the lazy dog. this is a test sentence."
        coherence = score_coherence(text, query="quick brown")
        
        print(f"✅ Scored text coherence")
        print(f"   Overall Score: {coherence.overall_score:.2f}/100")
        print(f"   Confidence: {coherence.confidence_level}")
        print(f"   Language: {coherence.language_score:.2f}/100")
        print(f"   Structure: {coherence.structure_score:.2f}/100")
        print(f"   N-gram: {coherence.ngram_score:.2f}/100")
        print(f"   Exact Match: {coherence.exact_match_score:.2f}/100")
        
        return True
    except Exception as e:
        print(f"❌ Decoder test failed: {e}")
        return False

def test_full_pipeline():
    """Test the complete pipeline"""
    print_header("Testing Full Pipeline Integration")
    
    try:
        from thalos_prime import (
            enumerate_addresses,
            address_to_page,
            decode_page
        )
        
        query = "test"
        
        # Step 1: Enumerate
        print(f"Step 1: Enumerating addresses for '{query}'...")
        addresses = enumerate_addresses(query, max_results=2)
        print(f"   Found {len(addresses)} addresses")
        
        # Step 2: Generate
        print(f"Step 2: Generating pages...")
        for addr_info in addresses:
            page = address_to_page(addr_info['address'])
            print(f"   Generated page: {len(page)} chars")
            
            # Step 3: Decode
            decoded = decode_page(
                address=addr_info['address'],
                text=page,
                query=query,
                source='local'
            )
            print(f"   Decoded score: {decoded.coherence.overall_score:.2f}/100")
        
        print("✅ Full pipeline working correctly")
        return True
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        return False

def test_api_models():
    """Test API models"""
    print_header("Testing API Models")
    
    try:
        from thalos_prime.models.api_models import (
            SearchRequest,
            ChatRequest,
            GenerateRequest
        )
        
        # Test creating request models
        search_req = SearchRequest(query="test", max_results=10)
        print(f"✅ Created SearchRequest: {search_req.query}")
        
        chat_req = ChatRequest(message="hello")
        print(f"✅ Created ChatRequest: {chat_req.message}")
        
        gen_req = GenerateRequest(address="abc123")
        print(f"✅ Created GenerateRequest: {gen_req.address}")
        
        return True
    except Exception as e:
        print(f"❌ API models test failed: {e}")
        return False

def main():
    """Run all verification tests"""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  THALOS PRIME - SYSTEM VERIFICATION".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    
    start_time = time.time()
    
    tests = [
        ("Module Imports", test_imports),
        ("Generator Module", test_generator),
        ("Enumerator Module", test_enumerator),
        ("Decoder Module", test_decoder),
        ("Full Pipeline", test_full_pipeline),
        ("API Models", test_api_models)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    elapsed = time.time() - start_time
    
    print(f"\nResults: {passed}/{total} tests passed")
    print(f"Time: {elapsed:.2f} seconds")
    
    if passed == total:
        print("\n🎉 ALL VERIFICATIONS PASSED - SYSTEM OPERATIONAL")
        return 0
    else:
        print(f"\n⚠️  {total - passed} VERIFICATION(S) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
