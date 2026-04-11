"""Search Routes - Direct search endpoints.

Provides search functionality with detailed results and filtering.
"""

import re
import time
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException
from fastapi import Query as QueryParam

from thalos_prime.lob_babel_enumerator import enumerate_addresses
from thalos_prime.lob_babel_generator import address_to_page
from thalos_prime.lob_decoder import decode_page
from thalos_prime.models.api_models import (
    AddressInfo,
    CoherenceInfo,
    ConfidenceLevel,
    PageResult,
    ProvenanceInfo,
    SearchMode,
    SearchRequest,
    SearchResponse,
)

router = APIRouter()

# Simple in-memory cache (replace with Redis in production)
SEARCH_CACHE: dict[str, tuple[dict[str, Any], float]] = {}
CACHE_TTL = 3600  # 1 hour

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "that", "the", "to", "with",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _query_terms(query: str) -> list[str]:
    return [term for term in _tokenize(query) if term not in STOPWORDS]


def _expand_query_variants(query: str) -> list[str]:
    """Build deterministic query variants for better candidate coverage."""
    terms = _query_terms(query)
    variants = [query.strip()]

    if terms:
        variants.append(" ".join(terms))
    if len(terms) >= 2:
        variants.append(" ".join(terms[:2]))
        variants.append(" ".join(terms[-2:]))
    variants.extend(terms[:4])

    seen: set[str] = set()
    deduped: list[str] = []
    for variant in variants:
        normalized = variant.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(variant.strip())

    return deduped[:8]


def _enumerate_ensemble_candidates(query: str, max_results: int) -> list[dict[str, Any]]:
    """Fuse candidates from multiple deterministic query variants."""
    variants = _expand_query_variants(query)
    if not variants:
        return []

    per_variant = max(4, min(16, max_results))
    fused: dict[str, dict[str, Any]] = {}

    for variant_index, variant in enumerate(variants):
        variant_weight = max(0.4, 1.0 - (variant_index * 0.1))
        candidates = enumerate_addresses(variant, max_results=per_variant, depth=2)

        for rank, candidate in enumerate(candidates, start=1):
            address = str(candidate["address"])
            rrf = variant_weight * (1.0 / (20 + rank))

            if address not in fused:
                fused[address] = {
                    "address": address,
                    "ensemble_score": 0.0,
                    "support_count": 0,
                    "ngrams": set(),
                }

            fused[address]["ensemble_score"] += rrf
            fused[address]["support_count"] += 1
            for ngram in candidate.get("ngrams", []):
                fused[address]["ngrams"].add(str(ngram))

    ranked = sorted(
        fused.values(),
        key=lambda item: (float(item["ensemble_score"]), int(item["support_count"])),
        reverse=True,
    )

    result: list[dict[str, Any]] = []
    for item in ranked[: max_results * 4]:
        result.append({
            "address": item["address"],
            "ensemble_score": item["ensemble_score"],
            "support_count": item["support_count"],
            "ngrams": sorted(item["ngrams"]),
        })
    return result


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    tokens_a = set(_tokenize(text_a))
    tokens_b = set(_tokenize(text_b))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def _combined_score(page: PageResult) -> float:
    metrics = page.coherence.metrics
    candidate = metrics.get("combined_score")
    if isinstance(candidate, int | float):
        return float(candidate)
    return float(page.coherence.overall_score)


def _diversify_results(
    results: list[PageResult],
    max_results: int,
    diversity_lambda: float,
) -> list[PageResult]:
    """Apply deterministic MMR reranking to reduce near-duplicate outputs."""
    ranked = sorted(results, key=_combined_score, reverse=True)
    selected: list[PageResult] = []

    while ranked and len(selected) < max_results:
        if not selected:
            selected.append(ranked.pop(0))
            continue

        best_idx = 0
        best_score = float("-inf")

        for idx, candidate in enumerate(ranked):
            relevance = _combined_score(candidate)
            redundancy = max(
                _jaccard_similarity(candidate.snippet or "", chosen.snippet or "")
                for chosen in selected
            )
            mmr_score = (diversity_lambda * relevance) - ((1.0 - diversity_lambda) * redundancy * 100.0)
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        selected.append(ranked.pop(best_idx))

    return selected


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


@router.post("/")
async def search(request: SearchRequest) -> SearchResponse:
    """Search for pages matching the query.

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
            results=cached_results["results"],
            total_found=cached_results["total_found"],
            mode=request.mode,
            cached=True,
            metadata={
                "query_time_ms": (time.time() - start_time) * 1000,
                "cache_hit": True,
            },
        )

    try:
        results = []

        if request.mode in [SearchMode.LOCAL, SearchMode.HYBRID]:
            # Local generation mode
            addresses = _enumerate_ensemble_candidates(
                request.query,
                max_results=request.max_results,
            )

            query_term_set = set(_query_terms(request.query))

            for addr_info in addresses:
                address = addr_info["address"]
                page_text = address_to_page(address)

                # Decode and score
                decoded = decode_page(
                    address=address,
                    text=page_text,
                    query=request.query,
                    source="local",
                )

                # Filter by minimum score
                if decoded.coherence.overall_score >= request.min_score:
                    page_terms = set(_tokenize(decoded.raw_text))
                    lexical_coverage = (
                        len(query_term_set & page_terms) / len(query_term_set)
                        if query_term_set
                        else 0.0
                    )
                    ensemble_score = float(addr_info.get("ensemble_score", 0.0))
                    combined_score = (
                        (decoded.coherence.overall_score * 0.75)
                        + (lexical_coverage * 100.0 * 0.20)
                        + (ensemble_score * 100.0 * 0.05)
                    )

                    metrics = dict(decoded.coherence.metrics)
                    metrics["lexical_coverage"] = lexical_coverage
                    metrics["ensemble_score"] = ensemble_score
                    metrics["support_count"] = int(addr_info.get("support_count", 1))
                    metrics["combined_score"] = combined_score

                    page_result = PageResult(
                        address=AddressInfo(
                            hex_address=address,
                            wall=None,
                            shelf=None,
                            volume=None,
                            page=None,
                            url=None,
                        ),
                        text=decoded.raw_text,
                        snippet=decoded.raw_text[:200] + "...",
                        normalized_text=None,
                        coherence=CoherenceInfo(
                            overall_score=decoded.coherence.overall_score,
                            language_score=decoded.coherence.language_score,
                            structure_score=decoded.coherence.structure_score,
                            ngram_score=decoded.coherence.ngram_score,
                            exact_match_score=decoded.coherence.exact_match_score,
                            confidence_level=ConfidenceLevel(decoded.coherence.confidence_level),
                            metrics=metrics,
                        ),
                        provenance=ProvenanceInfo(
                            address=decoded.address,
                            source=decoded.source,
                            query=request.query,
                            timestamp=decoded.timestamp,
                            normalized=False,
                            llm_provider=None,
                        ),
                    )
                    results.append(page_result)

        results = _diversify_results(
            results,
            max_results=request.max_results,
            diversity_lambda=request.diversity_lambda,
        )

        # Cache results
        cache_data = {
            "results": results,
            "total_found": len(results),
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
                "query_time_ms": query_time_ms,
                "cache_hit": False,
                "addresses_enumerated": len(addresses) if "addresses" in locals() else 0,
                "query_variants": _expand_query_variants(request.query),
                "diversity_lambda": request.diversity_lambda,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}")


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
