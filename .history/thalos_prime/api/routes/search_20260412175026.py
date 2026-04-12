"""Search Routes - Direct search endpoints.

Provides search functionality with detailed results and filtering.
"""

import time
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException
from fastapi import Query as QueryParam

from thalos_prime.models.api_models import (
    PageResult,
    RemoteAccessPolicy,
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


def _intent_profile(query: str) -> dict[str, Any]:
    """Classify query intent and return deterministic weighting profile."""
    lowered = query.lower()
    definition_tokens = ("define", "definition", "meaning", "what is", "explain")
    exploratory_tokens = ("explore", "relationship", "patterns", "compare", "discover")

    if any(token in lowered for token in definition_tokens):
        return {
            "label": "definition",
            "coherence_weight": 0.60,
            "lexical_weight": 0.25,
            "ensemble_weight": 0.15,
        }

    if any(token in lowered for token in exploratory_tokens):
        return {
            "label": "exploratory",
            "coherence_weight": 0.45,
            "lexical_weight": 0.35,
            "ensemble_weight": 0.20,
        }

    return {
        "label": "balanced",
        "coherence_weight": 0.50,
        "lexical_weight": 0.30,
        "ensemble_weight": 0.20,
    }


def _is_remote_allowed(request: SearchRequest) -> tuple[bool, str]:
    """Evaluate remote access policy with explicit rationale."""
    if request.remote_access_policy == RemoteAccessPolicy.LOCAL_ONLY:
        return False, "remote_access_policy=local_only"
    if request.remote_access_policy in {
        RemoteAccessPolicy.ALWAYS_ALLOW,
        RemoteAccessPolicy.ALLOW_REMOTE,
    }:
        return True, "allowed"
    if request.remote_consent:
        return True, "allowed"
    return False, "remote_consent_required"


def _rank_score(
    *,
    coherence_overall: float,
    lexical_coverage: float,
    ensemble_score: float,
    profile: dict[str, Any],
    source_weight: float,
) -> float:
    """Compute deterministic weighted rank score."""
    coherence_component = (coherence_overall / 100.0) * float(profile["coherence_weight"])
    lexical_component = lexical_coverage * float(profile["lexical_weight"])
    ensemble_component = ensemble_score * float(profile["ensemble_weight"])
    return (coherence_component + lexical_component + ensemble_component) * source_weight


def _effective_diversity_lambda(
    request: SearchRequest,
    profile: dict[str, Any],
    query_term_count: int,
) -> float:
    """Adapt diversity lambda by intent and query complexity when enabled."""
    base = request.diversity_lambda
    if not request.enable_adaptive_optimization:
        return base

    label = str(profile.get("label", "balanced"))
    complexity_adjustment = min(0.12, max(0.0, (query_term_count - 2) * 0.02))

    if label == "definition":
        return min(1.0, base + 0.10)
    if label == "exploratory":
        return max(0.0, base - (0.08 + complexity_adjustment))
    return min(1.0, max(0.0, base - 0.02))


def _expand_query_variants(query: str) -> list[str]:
    """Return deterministic query variants with original query first."""
    normalized = " ".join(query.split())
    lowered = normalized.lower()
    variants = [normalized]

    if lowered != normalized:
        variants.append(lowered)

    tokens = [token for token in lowered.split(" ") if token]
    unique_tokens = sorted(set(tokens))
    if unique_tokens:
        variants.append(" ".join(unique_tokens))

    # Preserve insertion order while deduplicating.
    seen: set[str] = set()
    ordered: list[str] = []
    for variant in variants:
        if variant not in seen:
            seen.add(variant)
            ordered.append(variant)
    return ordered


def _token_jaccard(text_a: str, text_b: str) -> float:
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def _diversify_results(
    results: list[PageResult],
    *,
    max_results: int,
    diversity_lambda: float,
) -> list[PageResult]:
    """Apply deterministic MMR-style reranking for diversity."""
    if max_results <= 0 or not results:
        return []

    effective_lambda = min(1.0, max(0.0, diversity_lambda))
    selected: list[PageResult] = [results[0]]
    remaining = list(results[1:])

    while remaining and len(selected) < max_results:
        best_idx = 0
        best_score = float("-inf")

        for idx, candidate in enumerate(remaining):
            base_score = float(candidate.coherence.metrics.get("combined_score", candidate.coherence.overall_score))
            max_similarity = max(
                (_token_jaccard(candidate.text, prior.text) for prior in selected),
                default=0.0,
            )
            mmr_score = ((1.0 - effective_lambda) * base_score) - (effective_lambda * max_similarity * 100.0)
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        selected.append(remaining.pop(best_idx))

    return selected[:max_results]


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
