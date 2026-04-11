"""Tests for intent weighting and remote federation policy controls."""

from __future__ import annotations

from thalos_prime.api.routes.search import _intent_profile, _is_remote_allowed, _rank_score
from thalos_prime.models.api_models import RemoteAccessPolicy, SearchRequest


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
