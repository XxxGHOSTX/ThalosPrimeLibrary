"""Tests for coherence threshold enforcement, generative mode, and CoherenceThresholdError.

Validates:
- Generative mode produces text with coherence >= 80 (deterministically).
- min_score enforcement raises CoherenceThresholdError for local/hybrid modes.
- CoherenceThresholdError contains a full deterministic state snapshot.
- GenerativeEngine is deterministic given fixed query + seed.
- /api/v1/chat endpoint correctly routes generative mode and enforces min_score.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from thalos_prime.api.server import app
from thalos_prime.errors import CoherenceThresholdError
from thalos_prime.generative_engine import (
    GenerativeEngine,
    generate_coherent_batch,
    generate_coherent_text,
)
from thalos_prime.lob_decoder import BabelDecoder
from thalos_prime.models.api_models import SearchMode


# ---------------------------------------------------------------------------
# GenerativeEngine unit tests
# ---------------------------------------------------------------------------


def test_generative_engine_deterministic_fixed_seed() -> None:
    """Given the same query and seed, the engine always returns the same text."""
    engine = GenerativeEngine()
    result1 = engine.generate("hello world", seed=42)
    result2 = engine.generate("hello world", seed=42)
    assert result1.text == result2.text
    assert result1.address == result2.address


def test_generative_engine_different_seeds_different_addresses() -> None:
    """Different seeds produce different addresses even for the same query."""
    engine = GenerativeEngine()
    result1 = engine.generate("thalos prime", seed=1)
    result2 = engine.generate("thalos prime", seed=2)
    # The deterministic address is derived from seed + query, so seeds differ → addresses differ.
    assert result1.address != result2.address
    # Seeds must also be recorded correctly.
    assert result1.seed == 1
    assert result2.seed == 2


def test_generative_engine_query_in_output() -> None:
    """The full query string must be present in the generated text."""
    engine = GenerativeEngine()
    query = "ThalosPrime deterministic overview"
    result = engine.generate(query, seed=999)
    assert query in result.text, "Full query must appear in generated text"


def test_generative_engine_coherence_above_80() -> None:
    """GenerativeEngine outputs must score >= 80 for various query types."""
    engine = GenerativeEngine()
    decoder = BabelDecoder()
    test_cases = [
        ("hello", 12345),
        ("ThalosPrime overview", 0),
        ("generate full detailed works", 99999),
        ("chat api query", 7),
        ("what is the system for", 314159),
        ("Generate a coherent full detailed ThalosPrimeLibrary overview with examples", 1),
    ]
    for query, seed in test_cases:
        result = engine.generate(query, seed=seed)
        score = decoder.score_coherence(result.text, query)
        assert score.overall_score >= 80.0, (
            f"Query {query!r} with seed {seed} scored {score.overall_score:.1f} < 80"
        )


def test_generate_coherent_text_convenience() -> None:
    """Convenience function scores >= 80."""
    decoder = BabelDecoder()
    result = generate_coherent_text("test query", seed=100)
    score = decoder.score_coherence(result.text, "test query")
    assert score.overall_score >= 80.0


def test_generate_coherent_batch_deterministic() -> None:
    """Batch generation is deterministic and each result scores >= 80."""
    decoder = BabelDecoder()
    batch1 = generate_coherent_batch("batch query", seed=55, count=3)
    batch2 = generate_coherent_batch("batch query", seed=55, count=3)
    assert len(batch1) == 3
    for r1, r2 in zip(batch1, batch2, strict=True):
        assert r1.text == r2.text, "Batch generation must be deterministic"
        score = decoder.score_coherence(r1.text, "batch query")
        assert score.overall_score >= 80.0


# ---------------------------------------------------------------------------
# CoherenceThresholdError unit tests
# ---------------------------------------------------------------------------


def test_coherence_threshold_error_fields() -> None:
    """CoherenceThresholdError exposes all required fields."""
    err = CoherenceThresholdError(
        min_score=80.0,
        best_score=19.5,
        attempts=5,
        time_budget_s=3.14,
        checkpoint={"task": "test", "seed": 1},
        mode="local",
    )
    assert err.min_score == 80.0
    assert err.best_score == 19.5
    assert err.attempts == 5
    assert err.mode == "local"
    assert "checkpoint" in err.state_snapshot


def test_coherence_threshold_error_to_dict() -> None:
    """to_dict() returns a fully serializable dict with required keys."""
    err = CoherenceThresholdError(
        min_score=80.0,
        best_score=19.5,
        attempts=3,
        time_budget_s=1.0,
        checkpoint={"task": "t", "seed": 0},
        mode="hybrid",
    )
    d = err.to_dict()
    assert d["error"] == "CoherenceThresholdError"
    assert isinstance(d["message"], str)
    assert "min_score" in d["state_snapshot"]
    assert "best_score" in d["state_snapshot"]
    assert "checkpoint" in d["state_snapshot"]


def test_coherence_threshold_error_is_exception() -> None:
    """CoherenceThresholdError can be raised and caught."""
    with pytest.raises(CoherenceThresholdError) as exc_info:
        raise CoherenceThresholdError(
            min_score=80.0,
            best_score=10.0,
            attempts=1,
            time_budget_s=0.0,
            checkpoint={},
            mode="local",
        )
    assert exc_info.value.min_score == 80.0


# ---------------------------------------------------------------------------
# SearchMode enum tests
# ---------------------------------------------------------------------------


def test_search_mode_generative_value() -> None:
    """SearchMode.GENERATIVE has value 'generative'."""
    assert SearchMode.GENERATIVE == "generative"
    assert SearchMode.GENERATIVE.value == "generative"


def test_search_mode_all_values() -> None:
    """SearchMode contains all four expected modes."""
    values = {m.value for m in SearchMode}
    assert values == {"local", "remote", "hybrid", "generative"}


# ---------------------------------------------------------------------------
# ChatRequest model tests
# ---------------------------------------------------------------------------


def test_chat_request_min_score_default() -> None:
    """ChatRequest.min_score defaults to 80.0."""
    from thalos_prime.models.api_models import ChatRequest

    req = ChatRequest(message="hello")
    assert req.min_score == 80.0


def test_chat_request_min_score_custom() -> None:
    """ChatRequest.min_score can be set to any value in [0, 100]."""
    from thalos_prime.models.api_models import ChatRequest

    req = ChatRequest(message="hello", min_score=0.0)
    assert req.min_score == 0.0

    req2 = ChatRequest(message="hello", min_score=50.0)
    assert req2.min_score == 50.0


def test_chat_request_generative_mode() -> None:
    """ChatRequest accepts mode='generative'."""
    from thalos_prime.models.api_models import ChatRequest

    req = ChatRequest(message="hello", mode=SearchMode.GENERATIVE)
    assert req.mode is SearchMode.GENERATIVE


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


def test_api_chat_generative_mode_success() -> None:
    """POST /api/v1/chat with generative mode returns 200 with high coherence."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "ThalosPrime overview",
                "mode": "generative",
                "max_results": 1,
                "min_score": 80.0,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["mode"] == "generative"
    assert len(body["results"]) >= 1
    assert body["results"][0]["coherence"]["overall_score"] >= 80.0


def test_api_chat_min_score_enforced_local_mode() -> None:
    """POST /api/v1/chat with local mode and min_score=80 returns 422."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "hello",
                "mode": "local",
                "max_results": 2,
                "min_score": 80.0,
            },
        )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "CoherenceThresholdError"
    snapshot = detail["state_snapshot"]
    assert snapshot["min_score"] == 80.0
    assert snapshot["best_score"] < 80.0
    assert "checkpoint" in snapshot


def test_api_chat_min_score_zero_allows_local() -> None:
    """POST /api/v1/chat with min_score=0 allows low-coherence local results."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "hello",
                "mode": "local",
                "max_results": 2,
                "min_score": 0.0,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert "results" in body


def test_api_chat_metadata_includes_llm_provider() -> None:
    """Generative mode metadata always includes llm_provider (None when not using LLM)."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "test",
                "mode": "generative",
                "max_results": 1,
                "min_score": 80.0,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert "llm_provider" in body["metadata"]
    assert body["metadata"]["llm_provider"] is None
