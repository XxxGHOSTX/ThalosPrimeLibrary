"""Search Routes - Direct search endpoints.

Provides search functionality with detailed results and filtering.
"""

import time
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException
from fastapi import Query as QueryParam

from thalos_prime.models.api_models import (
    SearchRequest,
    SearchResponse,
)
from thalos_runtime.core.deps import get_engine
from thalos_runtime.core.executor import ExecutionError
from thalos_runtime.core.registry import RegistryError

router = APIRouter()

# Simple in-memory cache (replace with Redis in production)
SEARCH_CACHE: dict[str, tuple[dict[str, Any], float]] = {}
CACHE_TTL = 3600  # 1 hour


def get_cached_search(cache_key: str) -> dict[str, Any] | None:
    """Get cached search results if available and not expired."""
    if cache_key in SEARCH_CACHE:
        cached_data, timestamp = SEARCH_CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return cached_data
        # Expired, remove from cache
        del SEARCH_CACHE[cache_key]
    return None


def cache_search(cache_key: str, data: dict[str, Any]) -> None:
    """Cache search results."""
    SEARCH_CACHE[cache_key] = (data, time.time())


@router.post("")
async def search(request: SearchRequest) -> SearchResponse:
    """Search for pages matching the query.

    This endpoint performs a search using the specified mode (local, remote, or hybrid),
    scores results by coherence, and returns the top matches.

    Args:
        request: Search request with query, mode, and filters

    Returns:
        SearchResponse with results and metadata

    """
    cache_key = f"{request.query}:{request.max_results}:{request.mode}:{request.min_score}"
    cached_results = get_cached_search(cache_key)
    if cached_results:
        cached_response = SearchResponse.model_validate(cached_results)
        metadata = dict(cached_response.metadata)
        metadata["cache_hit"] = True
        return cached_response.model_copy(update={"cached": True, "metadata": metadata})
    try:
        result = get_engine().execute("search.v1.query", request.model_dump())
        response = SearchResponse.model_validate(result)
        cache_search(cache_key, response.model_dump())
        return response
    except RegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExecutionError as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc


@router.get("/suggestions")
async def get_search_suggestions(q: Annotated[str, QueryParam(min_length=1)]) -> dict[str, Any]:
    """Get search query suggestions.

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
        f"{q} theory",
    ]

    return {
        "query": q,
        "suggestions": suggestions[:5],
    }


@router.delete("/cache")
async def clear_search_cache() -> dict[str, Any]:
    """Clear the search cache.

    Returns:
        Success message with number of entries cleared

    """
    count = len(SEARCH_CACHE)
    SEARCH_CACHE.clear()

    return {
        "message": "Search cache cleared successfully",
        "entries_cleared": count,
    }


@router.get("/cache/stats")
async def get_cache_stats() -> dict[str, Any]:
    """Get search cache statistics.

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
        "total_entries": total_entries,
        "avg_size_bytes": int(avg_size),
        "avg_age_seconds": int(avg_age),
        "cache_ttl_seconds": CACHE_TTL,
    }
