"""
Search Routes - Direct search endpoints

Provides search functionality with detailed results and filtering.
"""

from fastapi import APIRouter, HTTPException, Query as QueryParam
from typing import List, Optional
import time

from thalos_prime.models.api_models import (
    SearchRequest,
    SearchResponse,
    PageResult,
    AddressInfo,
    CoherenceInfo,
    ProvenanceInfo,
    SearchMode
)
from thalos_prime.lob_babel_generator import address_to_page
from thalos_prime.lob_babel_enumerator import enumerate_addresses
from thalos_prime.lob_decoder import decode_page, score_coherence

router = APIRouter()

# Simple in-memory cache (replace with Redis in production)
SEARCH_CACHE = {}
CACHE_TTL = 3600  # 1 hour


def get_cached_search(cache_key: str) -> Optional[dict]:
    """Get cached search results if available and not expired"""
    if cache_key in SEARCH_CACHE:
        cached_data, timestamp = SEARCH_CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return cached_data
        else:
            # Expired, remove from cache
            del SEARCH_CACHE[cache_key]
    return None


def cache_search(cache_key: str, data: dict):
    """Cache search results"""
    SEARCH_CACHE[cache_key] = (data, time.time())


@router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search for pages matching the query.
    
    This endpoint performs a search using the specified mode (local, remote, or hybrid),
    scores results by coherence, and returns the top matches.
    
    Args:
        request: Search request with query, mode, and filters
    
    Returns:
        SearchResponse with results and metadata
    """
    start_time = time.time()
    
    # Create cache key
    cache_key = f"{request.query}:{request.max_results}:{request.mode}:{request.min_score}"
    
    # Check cache
    cached_results = get_cached_search(cache_key)
    if cached_results:
        return SearchResponse(
            query=request.query,
            results=cached_results['results'],
            total_found=cached_results['total_found'],
            mode=request.mode,
            cached=True,
            metadata={
                'query_time_ms': (time.time() - start_time) * 1000,
                'cache_hit': True
            }
        )
    
    try:
        results = []
        
        if request.mode in [SearchMode.LOCAL, SearchMode.HYBRID]:
            # Local generation mode
            addresses = enumerate_addresses(
                request.query,
                max_results=request.max_results * 2,  # Get more to filter
                depth=2
            )
            
            for addr_info in addresses:
                address = addr_info['address']
                page_text = address_to_page(address)
                
                # Decode and score
                decoded = decode_page(
                    address=address,
                    text=page_text,
                    query=request.query,
                    source='local'
                )
                
                # Filter by minimum score
                if decoded.coherence.overall_score >= request.min_score:
                    page_result = PageResult(
                        address=AddressInfo(hex_address=address),
                        text=decoded.raw_text,
                        snippet=decoded.raw_text[:200] + "...",
                        coherence=CoherenceInfo(
                            overall_score=decoded.coherence.overall_score,
                            language_score=decoded.coherence.language_score,
                            structure_score=decoded.coherence.structure_score,
                            ngram_score=decoded.coherence.ngram_score,
                            exact_match_score=decoded.coherence.exact_match_score,
                            confidence_level=decoded.coherence.confidence_level,
                            metrics=decoded.coherence.metrics
                        ),
                        provenance=ProvenanceInfo(
                            address=decoded.address,
                            source=decoded.source,
                            query=request.query,
                            timestamp=decoded.timestamp,
                            normalized=False
                        )
                    )
                    results.append(page_result)
        
        # Sort by coherence score
        results.sort(key=lambda x: x.coherence.overall_score, reverse=True)
        
        # Limit to max_results
        results = results[:request.max_results]
        
        # Cache results
        cache_data = {
            'results': results,
            'total_found': len(results)
        }
        cache_search(cache_key, cache_data)
        
        # Calculate query time
        query_time_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_found=len(results),
            mode=request.mode,
            cached=False,
            metadata={
                'query_time_ms': query_time_ms,
                'cache_hit': False,
                'addresses_enumerated': len(addresses) if 'addresses' in locals() else 0
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/suggestions")
async def get_search_suggestions(q: str = QueryParam(..., min_length=1)):
    """
    Get search query suggestions.
    
    Args:
        q: Partial query string
    
    Returns:
        List of suggested queries
    """
    # This would normally query a database or search index
    # For now, return some example suggestions
    suggestions = [
        f"{q} meaning",
        f"{q} definition",
        f"{q} explained",
        f"{q} analysis",
        f"{q} theory"
    ]
    
    return {
        'query': q,
        'suggestions': suggestions[:5]
    }


@router.delete("/cache")
async def clear_search_cache():
    """
    Clear the search cache.
    
    Returns:
        Success message with number of entries cleared
    """
    count = len(SEARCH_CACHE)
    SEARCH_CACHE.clear()
    
    return {
        'message': 'Search cache cleared successfully',
        'entries_cleared': count
    }


@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get search cache statistics.
    
    Returns:
        Cache statistics
    """
    total_entries = len(SEARCH_CACHE)
    
    # Calculate cache size and age
    cache_sizes = []
    cache_ages = []
    current_time = time.time()
    
    for cached_data, timestamp in SEARCH_CACHE.values():
        # Rough size estimation
        cache_sizes.append(len(str(cached_data)))
        cache_ages.append(current_time - timestamp)
    
    avg_size = sum(cache_sizes) / len(cache_sizes) if cache_sizes else 0
    avg_age = sum(cache_ages) / len(cache_ages) if cache_ages else 0
    
    return {
        'total_entries': total_entries,
        'avg_size_bytes': int(avg_size),
        'avg_age_seconds': int(avg_age),
        'cache_ttl_seconds': CACHE_TTL
    }
