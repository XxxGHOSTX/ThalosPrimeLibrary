"""Tests for intent weighting and remote federation policy controls."""

from __future__ import annotations

from thalos_prime.api.routes.search import (
    _effective_diversity_lambda,
    _intent_profile,
    _is_remote_allowed,
    _rank_score,
    _search_cache_key,
)
from thalos_prime.models.api_models import RemoteAccessPolicy, SearchMode, SearchRequest


def test_intent_profile_definition_bias() -> None:
    profile = _intent_profile("define the meaning of coherence")
    assert profile["label"] == "definition"
    assert profile["coherence_weight"] >= profile["ensemble_weight"]


def test_intent_profile_exploratory_bias() -> None:
    profile = _intent_profile("explore patterns and relationships in graph reasoning")
    assert profile["label"] == "exploratory"
    assert profile["ensemble_weight"] >= 0.10


def test_remote_policy_blocks_without_consent() -> None:
    request = SearchRequest(
        query="test",
        remote_access_policy=RemoteAccessPolicy.CONSENT_REQUIRED,
        remote_consent=False,
    )
    allowed, reason = _is_remote_allowed(request)
    assert allowed is False
    assert "remote_consent" in reason


def test_remote_policy_allows_with_consent() -> None:
    request = SearchRequest(
        query="test",
        remote_access_policy=RemoteAccessPolicy.CONSENT_REQUIRED,
        remote_consent=True,
    )
    allowed, reason = _is_remote_allowed(request)
    assert allowed is True
    assert reason == "allowed"


def test_source_weight_increases_rank_score() -> None:
    profile = _intent_profile("what is deterministic search")
    low = _rank_score(
        coherence_overall=60.0,
        lexical_coverage=0.5,
        ensemble_score=0.2,
        profile=profile,
        source_weight=0.8,
    )
    high = _rank_score(
        coherence_overall=60.0,
        lexical_coverage=0.5,
        ensemble_score=0.2,
        profile=profile,
        source_weight=1.2,
    )
    assert high > low


def test_adaptive_lambda_definition_prefers_relevance() -> None:
    request = SearchRequest(
        query="define coherence",
        diversity_lambda=0.60,
        enable_adaptive_optimization=True,
    )
    profile = _intent_profile(request.query)
    effective = _effective_diversity_lambda(request, profile, query_term_count=2)
    assert effective > request.diversity_lambda


def test_adaptive_lambda_exploratory_balances_diversity() -> None:
    request = SearchRequest(
        query="explore graph language reasoning patterns",
        diversity_lambda=0.80,
        enable_adaptive_optimization=True,
    )
    profile = _intent_profile(request.query)
    effective = _effective_diversity_lambda(request, profile, query_term_count=5)
    assert effective < request.diversity_lambda


def test_cache_key_changes_when_request_controls_change() -> None:
    base = SearchRequest(
        query="deterministic benchmark cache key",
        max_results=5,
        mode=SearchMode.HYBRID,
        min_score=79.0,
        remote_access_policy=RemoteAccessPolicy.CONSENT_REQUIRED,
        remote_consent=False,
        enable_query_expansion=False,
        enable_diversity_rerank=False,
        enable_adaptive_optimization=False,
        diversity_lambda=0.7,
    )
    stricter_threshold = base.model_copy(update={"min_score": 90.0})
    changed_diversity = base.model_copy(update={"enable_diversity_rerank": True, "diversity_lambda": 0.2})
    changed_remote = base.model_copy(
        update={"remote_access_policy": RemoteAccessPolicy.ALWAYS_ALLOW, "remote_consent": True},
    )

    base_key = _search_cache_key(base)
    assert _search_cache_key(stricter_threshold) != base_key
    assert _search_cache_key(changed_diversity) != base_key
    assert _search_cache_key(changed_remote) != base_key
