"""
Enumerate Routes - Address enumeration endpoints

Provides query-to-address mapping functionality.
"""

from fastapi import APIRouter, HTTPException
from typing import Any
import time

from thalos_prime.models.api_models import (
    EnumerateRequest,
    EnumerateResponse
)
from thalos_prime.lob_babel_enumerator import enumerate_addresses, query_to_addresses, BabelEnumerator

router = APIRouter()
enumerator = BabelEnumerator()


@router.post("/", response_model=EnumerateResponse)
async def enumerate(request: EnumerateRequest) -> EnumerateResponse:
    """
    Enumerate addresses for a query.
    
    Breaks down the query into n-grams and generates candidate addresses
    where matching content might be found.
    
    Args:
        request: Enumerate request with query and parameters
    
    Returns:
        EnumerateResponse with addresses and metadata
    """
    start_time = time.time()
    
    try:
        # Enumerate addresses
        results = enumerate_addresses(
            request.query,
            max_results=request.max_results,
            depth=request.depth
        )
        
        # Calculate enumeration time
        enumeration_time_ms = (time.time() - start_time) * 1000
        
        return EnumerateResponse(
            query=request.query,
            addresses=results,
            total_found=len(results),
            metadata={
                'enumeration_time_ms': enumeration_time_ms,
                'depth': request.depth,
                'avg_score': sum(r['score'] for r in results) / len(results) if results else 0
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enumeration failed: {str(e)}")


@router.get("/addresses")
async def get_addresses_only(query: str, count: int = 10) -> dict[str, Any]:
    """
    Get just the addresses without metadata.
    
    Args:
        query: Query string
        count: Number of addresses to return
    
    Returns:
        List of hex addresses
    """
    try:
        addresses = query_to_addresses(query, count=count)
        
        return {
            'query': query,
            'addresses': addresses,
            'count': len(addresses)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Address enumeration failed: {str(e)}")


@router.post("/ngrams")
async def extract_ngrams(text: str, min_size: int = 2, max_size: int = 5) -> dict[str, Any]:
    """
    Extract n-grams from text.
    
    Args:
        text: Text to extract n-grams from
        min_size: Minimum n-gram size
        max_size: Maximum n-gram size
    
    Returns:
        List of n-grams
    """
    try:
        # Create enumerator with custom sizes
        custom_enumerator = BabelEnumerator(
            max_ngram_size=max_size,
            min_ngram_size=min_size
        )
        
        ngrams = custom_enumerator._extract_ngrams(text)
        
        return {
            'text': text,
            'ngrams': ngrams,
            'count': len(ngrams),
            'min_size': min_size,
            'max_size': max_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"N-gram extraction failed: {str(e)}")


@router.post("/common")
async def find_common_addresses(query1: str, query2: str, max_results: int = 10) -> dict[str, Any]:
    """
    Find addresses that might contain both queries.
    
    Args:
        query1: First query
        query2: Second query
        max_results: Maximum number of common addresses
    
    Returns:
        List of common addresses
    """
    try:
        common = enumerator.find_common_addresses(query1, query2, max_results=max_results)
        
        return {
            'query1': query1,
            'query2': query2,
            'common_addresses': common,
            'count': len(common)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Common address search failed: {str(e)}")


@router.post("/substrings")
async def enumerate_substrings(text: str, substring_length: int = 10) -> dict[str, Any]:
    """
    Enumerate all substrings of a given length.
    
    Args:
        text: Text to extract substrings from
        substring_length: Length of substrings
    
    Returns:
        List of substring-address pairs
    """
    try:
        results = enumerator.enumerate_substrings(text, substring_length=substring_length)
        
        return {
            'text': text,
            'substring_length': substring_length,
            'results': [
                {'substring': sub, 'address': addr}
                for sub, addr in results[:100]  # Limit to 100 for performance
            ],
            'total_count': len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Substring enumeration failed: {str(e)}")
