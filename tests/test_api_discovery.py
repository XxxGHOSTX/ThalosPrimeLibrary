"""API contract tests for discovery analysis."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from thalos_prime.api.routes.discovery import router


def _client() -> TestClient:
    """Build a route-only application for isolated contract tests."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_discovery_endpoint_returns_falsifiable_candidate() -> None:
    response = _client().post("/analyze", json={
        "question": "Find a bottleneck limiting throughput",
        "constraints": [{"name": "min", "left_variable": "throughput",
                         "operator": "ge", "right_value": 10}],
        "values": {"throughput": 7},
    })
    assert response.status_code == 200
    body = response.json()
    assert body["hypotheses"][0]["falsifier"]
    assert body["hypotheses"][0]["status"] == "candidate"
    assert body["constraint_results"][0]["status"] == "violated"
    assert body["limitations"]


def test_discovery_endpoint_rejects_reproducible_observation_without_hash() -> None:
    response = _client().post("/analyze", json={
        "question": "capacity bottleneck",
        "observations": [{
            "observation_id": "o", "hypothesis_id": "h", "outcome": "supports",
            "method": "repeat the experiment", "reproducible": True,
        }],
    })
    assert response.status_code == 422


def test_discovery_endpoint_reports_structured_conflict() -> None:
    response = _client().post("/analyze", json={
        "question": "state transition",
        "claims": [
            {"claim_id": "yes", "text": "A holds", "proposition_key": "A", "polarity": True},
            {"claim_id": "no", "text": "A does not hold", "proposition_key": "A", "polarity": False},
        ],
    })
    assert response.status_code == 200
    assert response.json()["contradictions"][0]["status"] == "conflict_requires_resolution"
