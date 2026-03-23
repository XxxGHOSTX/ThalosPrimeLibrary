"""Enumerate Routes - Address enumeration endpoints.

Provides query-to-address mapping functionality.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from thalos_prime.lob_babel_enumerator import (
    BabelEnumerator,
    query_to_addresses,
)
from thalos_prime.models.api_models import EnumerateRequest, EnumerateResponse
from thalos_runtime.core.deps import get_engine
from thalos_runtime.core.executor import ExecutionError
from thalos_runtime.core.registry import RegistryError

router = APIRouter()
enumerator = BabelEnumerator()


@router.post("")
async def enumerate(request: EnumerateRequest) -> EnumerateResponse:
    """Enumerate addresses for a query.

    Breaks down the query into n-grams and generates candidate addresses
    where matching content might be found.

    Args:
        request: Enumerate request with query and parameters

    Returns:
        EnumerateResponse with addresses and metadata

    """
    try:
        result = get_engine().execute("babel.v1.enumerate", request.model_dump())
        return EnumerateResponse.model_validate(result)
    except RegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExecutionError as exc:
        raise HTTPException(status_code=500, detail=f"Enumeration failed: {exc}") from exc


@router.get("/addresses")
async def get_addresses_only(query: str, count: int = 10) -> dict[str, Any]:
    """Get just the addresses without metadata.

    Args:
        query: Query string
        count: Number of addresses to return

    Returns:
        List of hex addresses

    """
    try:
        addresses = query_to_addresses(query, count=count)

        return {
            "query": query,
            "addresses": addresses,
            "count": len(addresses),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Address enumeration failed: {e!s}")


@router.post("/ngrams")
async def extract_ngrams(text: str, min_size: int = 2, max_size: int = 5) -> dict[str, Any]:
    """Extract n-grams from text.

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
            min_ngram_size=min_size,
        )

        ngrams = custom_enumerator._extract_ngrams(text)

        return {
            "text": text,
            "ngrams": ngrams,
            "count": len(ngrams),
            "min_size": min_size,
            "max_size": max_size,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"N-gram extraction failed: {e!s}")


@router.post("/common")
async def find_common_addresses(query1: str, query2: str, max_results: int = 10) -> dict[str, Any]:
    """Find addresses that might contain both queries.

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
            "query1": query1,
            "query2": query2,
            "common_addresses": common,
            "count": len(common),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Common address search failed: {e!s}")


@router.post("/substrings")
async def enumerate_substrings(text: str, substring_length: int = 10) -> dict[str, Any]:
    """Enumerate all substrings of a given length.

    Args:
        text: Text to extract substrings from
        substring_length: Length of substrings

    Returns:
        List of substring-address pairs

    """
    try:
        results = enumerator.enumerate_substrings(text, substring_length=substring_length)

        return {
            "text": text,
            "substring_length": substring_length,
            "results": [
                {"substring": sub, "address": addr}
                for sub, addr in results[:100]  # Limit to 100 for performance
            ],
            "total_count": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Substring enumeration failed: {e!s}")
