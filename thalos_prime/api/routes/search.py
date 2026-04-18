"""Search Routes - Direct search endpoints.

Provides search functionality with detailed results and filtering.
All results are guaranteed to have coherence.overall_score >= 79.0 via the
AdaptiveCoherenceSearch engine.  The search can run for up to 30 minutes if
needed; in practice Stage 1 (GenerativeEngine corpus) always resolves queries
in under one second.
"""

import json
import time
from typing import Annotated, Any

from fastapi import APIRouter
from fastapi import Query as QueryParam

from thalos_prime.adaptive_search import AdaptiveResult, adaptive_search
from thalos_prime.individuation import build_individuation_profile
from thalos_prime.models.api_models import (
    AddressInfo,
    CoherenceInfo,
    PageResult,
    ProvenanceInfo,
    RemoteAccessPolicy,
    SearchRequest,
    SearchResponse,
)

router = APIRouter()

# Minimum score enforced globally on every search result
_MIN_COHERENCE_SCORE: float = 79.0

# Simple in-memory cache (replace with Redis in production)
SEARCH_CACHE: dict[str, tuple[dict[str, Any], float]] = {}
CACHE_TTL = 3600  # 1 hour

# Purity functional weights (sum of positive terms is 1.0 by convention).
_PURITY_ALPHA = 0.35  # coherence
_PURITY_BETA = 0.20  # determinism
_PURITY_GAMMA = 0.20  # constraint satisfaction
_PURITY_DELTA = 0.25  # provenance integrity
_PURITY_LAMBDA = 0.15  # entropy leak penalty


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

    seen: set[str] = set()
    ordered: list[str] = []
    for variant in variants:
        if variant not in seen:
            seen.add(variant)
            ordered.append(variant)
    return ordered


def _tokenize(text: str) -> set[str]:
    return {token for token in text.lower().split() if token}


def _token_jaccard_tokens(tokens_a: set[str], tokens_b: set[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def _token_jaccard(text_a: str, text_b: str) -> float:
    return _token_jaccard_tokens(_tokenize(text_a), _tokenize(text_b))


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))


def _query_coverage(text: str, query: str) -> float:
    query_terms = {token for token in query.lower().split() if token}
    if not query_terms:
        return 0.0
    text_terms = set(text.lower().split())
    if not text_terms:
        return 0.0
    return len(query_terms & text_terms) / len(query_terms)


def _entropy_leak(text: str, query: str) -> float:
    """Estimate entropy leak as ungrounded lexical variance in [0,1]."""
    tokens = [token for token in text.lower().split() if token]
    if not tokens:
        return 1.0
    unique_ratio = len(set(tokens)) / len(tokens)
    groundedness = _query_coverage(text, query)
    return _clamp01(unique_ratio * (1.0 - groundedness))


def _provenance_integrity(result: PageResult) -> float:
    prov = result.provenance
    checks = [
        bool(prov.address),
        bool(prov.source),
        bool(prov.query),
        prov.timestamp > 0,
    ]
    return sum(1.0 for check in checks if check) / float(len(checks))


def _constraint_satisfaction(result: PageResult, effective_min: float) -> float:
    if result.coherence.overall_score < effective_min:
        return 0.0
    return 1.0


def _novelty(result: PageResult, peers: list[PageResult], token_sets: dict[int, set[str]]) -> float:
    result_tokens = token_sets[id(result)]
    max_similarity = max(
        (
            _token_jaccard_tokens(result_tokens, token_sets[id(peer)])
            for peer in peers
            if peer is not result
        ),
        default=0.0,
    )
    return _clamp01(1.0 - max_similarity)


def _compute_purity_metrics(
    result: PageResult,
    *,
    peers: list[PageResult],
    query: str,
    effective_min: float,
    token_sets: dict[int, set[str]],
) -> dict[str, float]:
    """Compute deterministic objective and purity functional components."""
    utility = _clamp01((result.coherence.overall_score / 100.0 + _query_coverage(result.text, query)) / 2.0)
    novelty = _novelty(result, peers, token_sets)
    feasibility = _constraint_satisfaction(result, effective_min)
    determinism = 1.0  # Adaptive search uses deterministic seeded generation.
    provenance = _provenance_integrity(result)
    explainability = _clamp01((determinism + provenance) / 2.0)
    entropy = _entropy_leak(result.text, query)

    objective = utility * novelty * feasibility * explainability
    purity = (
        (_PURITY_ALPHA * (result.coherence.overall_score / 100.0))
        + (_PURITY_BETA * determinism)
        + (_PURITY_GAMMA * feasibility)
        + (_PURITY_DELTA * provenance)
        - (_PURITY_LAMBDA * entropy)
    )

    return {
        "utility": utility,
        "novelty": novelty,
        "feasibility": feasibility,
        "explainability": explainability,
        "determinism": determinism,
        "provenance_integrity": provenance,
        "entropy_leak": entropy,
        "objective_score": _clamp01(objective),
        "purity_score": _clamp01(purity),
    }


def _annotate_purity_metrics(
    results: list[PageResult],
    *,
    query: str,
    effective_min: float,
    loop_cycle: int,
) -> None:
    """Attach purity metrics to each result without mutating ranking order."""
    token_sets = {id(result): _tokenize(result.text) for result in results}
    for result in results:
        purity = _compute_purity_metrics(
            result,
            peers=results,
            query=query,
            effective_min=effective_min,
            token_sets=token_sets,
        )
        result.coherence.metrics["purity"] = {
            "loop_cycle": loop_cycle,
            **purity,
        }


def _purity_mean(results: list[PageResult]) -> float:
    if not results:
        return 0.0
    scores = [
        float(result.coherence.metrics.get("purity", {}).get("purity_score", 0.0))
        for result in results
    ]
    return sum(scores) / len(scores)


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
    selected_token_sets: list[set[str]] = [_tokenize(results[0].text)]
    remaining: list[tuple[PageResult, set[str]]] = [
        (result, _tokenize(result.text))
        for result in results[1:]
    ]

    while remaining and len(selected) < max_results:
        best_idx = 0
        best_score = float("-inf")

        for idx, (candidate, candidate_tokens) in enumerate(remaining):
            base_score = float(candidate.coherence.metrics.get("combined_score", candidate.coherence.overall_score))
            max_similarity = max(
                (
                    _token_jaccard_tokens(candidate_tokens, prior_token_set)
                    for prior_token_set in selected_token_sets
                ),
                default=0.0,
            )
            mmr_score = ((1.0 - effective_lambda) * base_score) - (effective_lambda * max_similarity * 100.0)
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        chosen, chosen_tokens = remaining.pop(best_idx)
        selected.append(chosen)
        selected_token_sets.append(chosen_tokens)

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


def _search_cache_key(request: SearchRequest) -> str:
    cache_key_payload = {
        "query": request.query,
        "max_results": request.max_results,
        "mode": request.mode.value,
        "min_score": request.min_score,
        "remote_access_policy": request.remote_access_policy.value,
        "remote_consent": request.remote_consent,
        "enable_query_expansion": request.enable_query_expansion,
        "enable_diversity_rerank": request.enable_diversity_rerank,
        "enable_adaptive_optimization": request.enable_adaptive_optimization,
        "diversity_lambda": request.diversity_lambda,
    }
    return f"adaptive:{json.dumps(cache_key_payload, sort_keys=True, separators=(',', ':'))}"


def _adaptive_result_to_page_result(ar: AdaptiveResult) -> PageResult:
    """Convert an AdaptiveResult to a PageResult suitable for SearchResponse.

    All AdaptiveResults are guaranteed to have overall_score >= 79.0.
    """
    cs = ar.coherence
    addr_info = AddressInfo(
        hex_address=ar.address,
        wall=None,
        shelf=None,
        volume=None,
        page=None,
        url=f"https://libraryofbabel.info/book.cgi?hex={ar.address}",
    )
    coherence_info = CoherenceInfo(
        overall_score=cs.overall_score,
        language_score=cs.language_score,
        structure_score=cs.structure_score,
        ngram_score=cs.ngram_score,
        exact_match_score=cs.exact_match_score,
        confidence_level=cs.confidence_level,  # type: ignore[arg-type]
        metrics=dict(cs.metrics),
    )
    provenance = ProvenanceInfo(
        address=ar.address,
        source="adaptive",
        query=ar.query,
        timestamp=time.time(),
        normalized=False,
        llm_provider=None,
    )
    return PageResult(
        address=addr_info,
        text=ar.text,
        snippet=ar.text[:200],
        coherence=coherence_info,
        provenance=provenance,
        normalized_text=None,
    )


@router.post("")
async def search(request: SearchRequest) -> SearchResponse:
    """Search for pages matching the query.

    All results are guaranteed to have coherence.overall_score >= 79.0.
    The adaptive search engine runs up to 30 minutes if necessary, but
    Stage 1 (GenerativeEngine corpus) resolves most queries in < 1 second.

    Args:
        request: Search request with query, mode, and filters

    Returns:
        SearchResponse with results, all scoring >= 79.0

    """
    return execute_search_request(request, use_cache=True)


def execute_search_request(request: SearchRequest, *, use_cache: bool = True) -> SearchResponse:
    """Execute the operational compiler search pipeline for a request.

    Args:
        request: Search request with query, mode, and scoring controls.
        use_cache: Whether to read/write the in-memory search cache.

    Returns:
        Fully scored SearchResponse with operational compiler metadata.

    """
    cache_key = _search_cache_key(request)
    if use_cache:
        cached_result = get_cached_search(cache_key)
        if cached_result:
            cached_response = SearchResponse.model_validate(cached_result)
            metadata = dict(cached_response.metadata)
            metadata["cache_hit"] = True
            return cached_response.model_copy(update={"cached": True, "metadata": metadata})

    # Run adaptive search — guaranteed >= 79.0 on all results
    adaptive_results = adaptive_search(
        request.query,
        max_results=request.max_results,
        timeout_seconds=1800.0,
    )

    query_profile = build_individuation_profile(request.query)
    page_results = [_adaptive_result_to_page_result(ar) for ar in adaptive_results]

    # Apply individuation metadata consistently to each result.
    for result in page_results:
        result_profile = build_individuation_profile(request.query, result.text)
        result.coherence.metrics["individuation"] = result_profile.as_metadata()

    # Apply any user-requested min_score filter (only raises the bar further)
    effective_min = max(_MIN_COHERENCE_SCORE, request.min_score)
    page_results = [
        pr for pr in page_results
        if pr.coherence.overall_score >= effective_min
    ]

    # Deterministic ranking: sort by overall_score descending
    page_results.sort(key=lambda pr: pr.coherence.overall_score, reverse=True)

    # Apply diversity reranking if requested
    if request.enable_diversity_rerank and len(page_results) > 1:
        profile = _intent_profile(request.query)
        lam = _effective_diversity_lambda(request, profile, len(request.query.split()))
        page_results = _diversify_results(
            page_results,
            max_results=request.max_results,
            diversity_lambda=lam,
        )

    # Operational purity compiler loop:
    # 1) annotate purity metrics, 2) optionally optimize selection by purity,
    # 3) re-annotate as a deterministic feedback cycle.
    _annotate_purity_metrics(
        page_results,
        query=request.query,
        effective_min=effective_min,
        loop_cycle=1,
    )
    cycle1_mean = _purity_mean(page_results)

    if request.enable_adaptive_optimization and len(page_results) > 1:
        page_results.sort(
            key=lambda result: float(result.coherence.metrics.get("purity", {}).get("purity_score", 0.0)),
            reverse=True,
        )

    _annotate_purity_metrics(
        page_results,
        query=request.query,
        effective_min=effective_min,
        loop_cycle=2,
    )
    cycle2_mean = _purity_mean(page_results)
    stabilized = abs(cycle2_mean - cycle1_mean) <= 1e-9

    response = SearchResponse(
        query=request.query,
        results=page_results,
        total_found=len(page_results),
        mode=request.mode,
        cached=False,
        metadata={
            "min_coherence_enforced": _MIN_COHERENCE_SCORE,
            "mode": request.mode.value,
            "individuation": query_profile.as_metadata(),
            "operational_compiler": {
                "objective": "argmax U*N*F*E subject to K<=0",
                "purity_functional": {
                    "alpha": _PURITY_ALPHA,
                    "beta": _PURITY_BETA,
                    "gamma": _PURITY_GAMMA,
                    "delta": _PURITY_DELTA,
                    "lambda": _PURITY_LAMBDA,
                },
                "feedback": {
                    "cycles": 2,
                    "cycle1_purity_mean": cycle1_mean,
                    "cycle2_purity_mean": cycle2_mean,
                    "stabilized": stabilized,
                },
            },
        },
    )
    if use_cache:
        cache_search(cache_key, response.model_dump())
    return response


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
