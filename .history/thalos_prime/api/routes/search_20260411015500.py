"""Search Routes - Direct search endpoints.

Provides search functionality with detailed results and filtering.
"""

import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Annotated, Any, Literal, TypedDict

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
    RemoteAccessPolicy,
    SearchMode,
    SearchRequest,
    SearchResponse,
)

router = APIRouter()

# Simple in-memory cache (replace with Redis in production)
SEARCH_CACHE: dict[str, tuple[dict[str, Any], float]] = {}
CACHE_TTL = 3600  # 1 hour
REMOTE_SEARCH_URL = "https://libraryofbabel.info/search.cgi"
REMOTE_TIMEOUT_S = 3
LOCAL_CORPUS_FALLBACK_PATH = "data/thalos_volume_dry_run.txt"
LOCAL_CORPUS_PAGE_SIZE = 3200
LOCAL_CORPUS_CACHE: list[str] | None = None

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "that", "the", "to", "with",
}

DEFINITION_HINTS = {
    "what", "define", "definition", "meaning", "means", "explain",
}
EXPLORATORY_HINTS = {
    "explore", "compare", "why", "how", "implications", "patterns", "relationships",
}


class IntentProfile(TypedDict):
    """Intent-specific weighting profile for adaptive ranking."""

    label: Literal["definition", "exploratory"]
    coherence_weight: float
    lexical_weight: float
    semantic_weight: float
    ensemble_weight: float


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


def _intent_profile(query: str) -> IntentProfile:
    """Classify query intent and return scoring weights."""
    terms = set(_tokenize(query))
    definition_score = len(terms & DEFINITION_HINTS)
    exploratory_score = len(terms & EXPLORATORY_HINTS)

    if definition_score >= exploratory_score:
        return {
            "label": "definition",
            "coherence_weight": 0.58,
            "lexical_weight": 0.20,
            "semantic_weight": 0.18,
            "ensemble_weight": 0.04,
        }
    return {
        "label": "exploratory",
        "coherence_weight": 0.50,
        "lexical_weight": 0.18,
        "semantic_weight": 0.17,
        "ensemble_weight": 0.15,
    }


def _is_remote_allowed(request: SearchRequest) -> tuple[bool, str]:
    if request.remote_access_policy == RemoteAccessPolicy.LOCAL_ONLY:
        return False, "remote access policy is local_only"
    if request.remote_access_policy == RemoteAccessPolicy.CONSENT_REQUIRED and not request.remote_consent:
        return False, "remote federation requires explicit remote_consent=true"
    return True, "allowed"


def _extract_remote_links(search_html: str) -> list[str]:
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', search_html, flags=re.IGNORECASE)
    results: list[str] = []
    for href in hrefs:
        if "book" not in href.lower() or "hex=" not in href.lower():
            continue
        link = urllib.parse.urljoin(REMOTE_SEARCH_URL, href)
        results.append(link)
    return list(dict.fromkeys(results))


def _extract_remote_text(page_html: str) -> str:
    pre_match = re.search(r"<pre[^>]*>(.*?)</pre>", page_html, flags=re.IGNORECASE | re.DOTALL)
    if pre_match:
        text = re.sub(r"\s+", " ", pre_match.group(1)).strip()
        if text:
            return text
    stripped = re.sub(r"<[^>]+>", " ", page_html)
    return re.sub(r"\s+", " ", stripped).strip()


def _query_overlap_score(query: str, candidate_text: str) -> float:
    query_tokens = set(_query_terms(query))
    candidate_tokens = set(_tokenize(candidate_text))
    if not query_tokens:
        return 0.0
    return len(query_tokens & candidate_tokens) / len(query_tokens)


def _load_local_corpus_pages() -> list[str]:
    global LOCAL_CORPUS_CACHE
    if LOCAL_CORPUS_CACHE is not None:
        return LOCAL_CORPUS_CACHE

    try:
        with open(LOCAL_CORPUS_FALLBACK_PATH, encoding="utf-8") as handle:
            content = handle.read()
    except OSError:
        LOCAL_CORPUS_CACHE = []
        return LOCAL_CORPUS_CACHE

    pages = [
        content[idx: idx + LOCAL_CORPUS_PAGE_SIZE]
        for idx in range(0, len(content), LOCAL_CORPUS_PAGE_SIZE)
        if content[idx: idx + LOCAL_CORPUS_PAGE_SIZE]
    ]
    LOCAL_CORPUS_CACHE = pages
    return pages


def _fetch_local_indexed_pages(query: str, max_results: int) -> list[dict[str, str]]:
    pages = _load_local_corpus_pages()
    if not pages:
        return []

    scored: list[tuple[float, int, str]] = []
    for idx, page_text in enumerate(pages):
        overlap = _query_overlap_score(query, page_text)
        scored.append((overlap, idx, page_text))

    ranked = sorted(scored, key=lambda item: (item[0], -item[1]), reverse=True)
    results: list[dict[str, str]] = []
    for overlap, idx, text in ranked[: max_results * 2]:
        if overlap <= 0.0:
            continue
        results.append(
            {
                "address": f"local-corpus-page-{idx + 1}",
                "url": LOCAL_CORPUS_FALLBACK_PATH,
                "text": text,
                "source": "local_indexed_fallback",
            },
        )
    return results[:max_results]


def _fetch_remote_pages(query: str, max_results: int) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Fetch remote pages from libraryofbabel.info for federation."""
    encoded = urllib.parse.urlencode({"find": query})
    search_url = f"{REMOTE_SEARCH_URL}?{encoded}"
    diagnostics: dict[str, Any] = {
        "query_url": search_url,
        "challenge_detected": False,
        "search_links_found": 0,
        "fallback_used": None,
        "error": None,
    }
    parsed_search = urllib.parse.urlparse(search_url)
    if parsed_search.scheme not in {"http", "https"}:
        diagnostics["error"] = "invalid_search_url_scheme"
        return _fetch_local_indexed_pages(query, max_results), diagnostics
    request = urllib.request.Request(  # noqa: S310
        search_url,
        headers={"User-Agent": "ThalosPrimeSearch/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=REMOTE_TIMEOUT_S) as response:  # noqa: S310
            search_html = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        diagnostics["error"] = f"search_fetch_failed:{exc!s}"
        diagnostics["fallback_used"] = "local_indexed_corpus"
        return _fetch_local_indexed_pages(query, max_results), diagnostics

    challenge_markers = ("cf_chl_opt", "Just a moment", "Enable JavaScript and cookies")
    if any(marker in search_html for marker in challenge_markers):
        diagnostics["challenge_detected"] = True
        diagnostics["error"] = "cloudflare_challenge"
        diagnostics["fallback_used"] = "local_indexed_corpus"
        return _fetch_local_indexed_pages(query, max_results), diagnostics

    links = _extract_remote_links(search_html)
    diagnostics["search_links_found"] = len(links)
    if not links:
        diagnostics["error"] = "no_remote_links_found"
        diagnostics["fallback_used"] = "local_indexed_corpus"
        return _fetch_local_indexed_pages(query, max_results), diagnostics
    pages: list[dict[str, str]] = []

    for link in links[: max_results * 2]:
        parsed_link = urllib.parse.urlparse(link)
        if parsed_link.scheme not in {"http", "https"}:
            continue
        page_request = urllib.request.Request(  # noqa: S310
            link,
            headers={"User-Agent": "ThalosPrimeSearch/1.0"},
        )
        try:
            with urllib.request.urlopen(page_request, timeout=REMOTE_TIMEOUT_S) as page_response:  # noqa: S310
                page_html = page_response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, ValueError):
            continue
        text = _extract_remote_text(page_html)
        if not text:
            continue
        parsed = urllib.parse.urlparse(link)
        hex_addr = urllib.parse.parse_qs(parsed.query).get("hex", [""])[0]
        pages.append(
            {
                "address": hex_addr or link,
                "url": link,
                "text": text,
                "source": "remote",
            },
        )

    if not pages:
        diagnostics["error"] = "remote_pages_empty"
        diagnostics["fallback_used"] = "local_indexed_corpus"
        return _fetch_local_indexed_pages(query, max_results), diagnostics

    return pages, diagnostics


def _enumerate_ensemble_candidates(query: str, max_results: int) -> list[dict[str, Any]]:
    """Fuse candidates from multiple deterministic query variants."""
    variants = _expand_query_variants(query)
    if not variants:
        return []

    term_count = len(_query_terms(query))
    per_variant = max(8, min(24, max_results * 2))
    depth = 3 if term_count >= 5 else 2
    fused: dict[str, dict[str, Any]] = {}

    for variant_index, variant in enumerate(variants):
        variant_weight = max(0.4, 1.0 - (variant_index * 0.1))
        candidates = enumerate_addresses(variant, max_results=per_variant, depth=depth)

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

    return [
        {
            "address": item["address"],
            "ensemble_score": item["ensemble_score"],
            "support_count": item["support_count"],
            "ngrams": sorted(item["ngrams"]),
        }
        for item in ranked[: max_results * 6]
    ]


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


def _chargram_similarity(text_a: str, text_b: str, size: int = 3) -> float:
    normalized_a = re.sub(r"\s+", " ", text_a.lower()).strip()
    normalized_b = re.sub(r"\s+", " ", text_b.lower()).strip()
    if len(normalized_a) < size or len(normalized_b) < size:
        return 0.0
    grams_a = {normalized_a[idx: idx + size] for idx in range(len(normalized_a) - size + 1)}
    grams_b = {normalized_b[idx: idx + size] for idx in range(len(normalized_b) - size + 1)}
    if not grams_a or not grams_b:
        return 0.0
    union = len(grams_a | grams_b)
    if union == 0:
        return 0.0
    return len(grams_a & grams_b) / union


def _semantic_alignment(query: str, candidate_text: str) -> float:
    query_tokens = " ".join(_query_terms(query))
    lexical = _jaccard_similarity(query_tokens, candidate_text)
    chargram = _chargram_similarity(query_tokens, candidate_text)
    return (0.55 * lexical) + (0.45 * chargram)


def _average_pairwise_similarity(results: list[PageResult]) -> float:
    snippets = [page.snippet or page.text for page in results]
    if len(snippets) < 2:
        return 0.0

    similarities: list[float] = []
    for left in range(len(snippets)):
        similarities.extend(
            _jaccard_similarity(snippets[left], snippets[right])
            for right in range(left + 1, len(snippets))
        )
    if not similarities:
        return 0.0
    return sum(similarities) / len(similarities)


def _effective_diversity_lambda(
    request: SearchRequest,
    profile: IntentProfile,
    query_term_count: int,
) -> float:
    if not request.enable_adaptive_optimization:
        return request.diversity_lambda

    if profile["label"] == "definition":
        target = 0.88 if query_term_count <= 2 else 0.82
    else:
        target = 0.62 if query_term_count >= 4 else 0.68

    blended = (request.diversity_lambda + target) / 2.0
    return max(0.0, min(1.0, blended))


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


def _rank_score(
    coherence_overall: float,
    lexical_coverage: float,
    ensemble_score: float,
    profile: IntentProfile,
    source_weight: float,
    semantic_alignment: float = 0.0,
) -> float:
    combined = (
        (coherence_overall * profile["coherence_weight"])
        + (lexical_coverage * 100.0 * profile["lexical_weight"])
        + (semantic_alignment * 100.0 * profile["semantic_weight"])
        + (ensemble_score * 100.0 * profile["ensemble_weight"])
    )
    return combined * source_weight


def _build_local_results(
    request: SearchRequest,
    query_term_set: set[str],
    intent_profile: IntentProfile,
) -> tuple[list[PageResult], list[dict[str, Any]]]:
    local_addresses = _enumerate_ensemble_candidates(
        request.query,
        max_results=request.max_results,
    ) if request.enable_query_expansion else enumerate_addresses(
        request.query,
        max_results=request.max_results * 3,
        depth=2,
    )

    results: list[PageResult] = []
    for addr_info in local_addresses:
        address = addr_info["address"]
        page_text = address_to_page(address)
        decoded = decode_page(
            address=address,
            text=page_text,
            query=request.query,
            source="local",
        )
        if decoded.coherence.overall_score < request.min_score:
            continue

        page_terms = set(_tokenize(decoded.raw_text))
        lexical_coverage = (
            len(query_term_set & page_terms) / len(query_term_set)
            if query_term_set
            else 0.0
        )
        semantic_alignment = _semantic_alignment(request.query, decoded.raw_text)
        ensemble_score = float(addr_info.get("ensemble_score", 0.0))
        combined_score = _rank_score(
            coherence_overall=decoded.coherence.overall_score,
            lexical_coverage=lexical_coverage,
            semantic_alignment=semantic_alignment,
            ensemble_score=ensemble_score,
            profile=intent_profile,
            source_weight=request.local_source_weight,
        )

        metrics = dict(decoded.coherence.metrics)
        metrics["lexical_coverage"] = lexical_coverage
        metrics["semantic_alignment"] = semantic_alignment
        metrics["ensemble_score"] = ensemble_score
        metrics["support_count"] = int(addr_info.get("support_count", 1))
        metrics["combined_score"] = combined_score
        metrics["intent_profile"] = intent_profile["label"]
        metrics["source_weight"] = request.local_source_weight

        results.append(
            PageResult(
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
            ),
        )

    return results, local_addresses


def _build_remote_results(
    request: SearchRequest,
    query_term_set: set[str],
    intent_profile: IntentProfile,
) -> tuple[list[PageResult], list[dict[str, str]], dict[str, Any]]:
    remote_pages, remote_diagnostics = _fetch_remote_pages(request.query, request.max_results)
    results: list[PageResult] = []

    for page in remote_pages:
        source = page.get("source", "remote")
        decoded = decode_page(
            address=page["address"],
            text=page["text"],
            query=request.query,
            source=source,
        )
        if decoded.coherence.overall_score < request.min_score:
            continue

        page_terms = set(_tokenize(decoded.raw_text))
        lexical_coverage = (
            len(query_term_set & page_terms) / len(query_term_set)
            if query_term_set
            else 0.0
        )
        semantic_alignment = _semantic_alignment(request.query, decoded.raw_text)
        combined_score = _rank_score(
            coherence_overall=decoded.coherence.overall_score,
            lexical_coverage=lexical_coverage,
            semantic_alignment=semantic_alignment,
            ensemble_score=0.0,
            profile=intent_profile,
            source_weight=request.remote_source_weight,
        )

        metrics = dict(decoded.coherence.metrics)
        metrics["lexical_coverage"] = lexical_coverage
        metrics["semantic_alignment"] = semantic_alignment
        metrics["ensemble_score"] = 0.0
        metrics["support_count"] = 1
        metrics["combined_score"] = combined_score
        metrics["intent_profile"] = intent_profile["label"]
        metrics["source_weight"] = request.remote_source_weight

        results.append(
            PageResult(
                address=AddressInfo(
                    hex_address=page["address"],
                    wall=None,
                    shelf=None,
                    volume=None,
                    page=None,
                    url=page["url"],
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
            ),
        )

    return results, remote_pages, remote_diagnostics


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
    cache_key = (
        f"{request.query}:{request.max_results}:{request.mode}:{request.min_score}:"
        f"{request.diversity_lambda}:{request.remote_access_policy}:{request.remote_consent}:"
        f"{request.local_source_weight}:{request.remote_source_weight}:"
        f"{request.enable_query_expansion}:{request.enable_diversity_rerank}:"
        f"{request.enable_adaptive_optimization}"
    )

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
        results: list[PageResult] = []
        intent_profile = _intent_profile(request.query)
        query_term_set = set(_query_terms(request.query))
        effective_diversity_lambda = _effective_diversity_lambda(
            request,
            profile=intent_profile,
            query_term_count=len(query_term_set),
        )
        local_addresses: list[dict[str, Any]] = []
        remote_pages: list[dict[str, str]] = []
        remote_diagnostics: dict[str, Any] = {}
        local_build_started = time.time()
        remote_allowed, remote_reason = _is_remote_allowed(request)

        if request.mode in [SearchMode.LOCAL, SearchMode.HYBRID]:
            local_results, local_addresses = _build_local_results(
                request,
                query_term_set=query_term_set,
                intent_profile=intent_profile,
            )
            results.extend(local_results)
        local_build_ms = (time.time() - local_build_started) * 1000.0

        remote_fetch_started = time.time()
        if request.mode in [SearchMode.REMOTE, SearchMode.HYBRID]:
            if request.mode == SearchMode.REMOTE and not remote_allowed:
                raise HTTPException(status_code=403, detail=f"Remote search blocked: {remote_reason}")

            if remote_allowed:
                remote_results, remote_pages, remote_diagnostics = _build_remote_results(
                    request,
                    query_term_set=query_term_set,
                    intent_profile=intent_profile,
                )
                results.extend(remote_results)
        remote_fetch_ms = (time.time() - remote_fetch_started) * 1000.0

        rerank_started = time.time()
        if request.enable_diversity_rerank:
            results = _diversify_results(
                results,
                max_results=request.max_results,
                diversity_lambda=effective_diversity_lambda,
            )
        else:
            results = sorted(results, key=_combined_score, reverse=True)[: request.max_results]
        rerank_ms = (time.time() - rerank_started) * 1000.0

        novelty_index = 1.0 - _average_pairwise_similarity(results)

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
                "addresses_enumerated": len(local_addresses),
                "remote_pages_federated": len(remote_pages),
                "query_variants": _expand_query_variants(request.query),
                "requested_diversity_lambda": request.diversity_lambda,
                "effective_diversity_lambda": effective_diversity_lambda,
                "intent_profile": intent_profile["label"],
                "adaptive_optimization": request.enable_adaptive_optimization,
                "novelty_index": novelty_index,
                "phase_timings_ms": {
                    "local_build": local_build_ms,
                    "remote_fetch": remote_fetch_ms,
                    "rerank": rerank_ms,
                },
                "remote_allowed": remote_allowed,
                "remote_block_reason": None if remote_allowed else remote_reason,
                "remote_diagnostics": remote_diagnostics,
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
