"""Regression tests for authentication boundaries on protected APIs."""

from fastapi.testclient import TestClient

from thalos_prime.api.server import app as prime_app
from thalos_runtime.api.server import app as runtime_app

TOKEN = "test-token-for-thalos-prime-tests-only"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def test_main_api_rejects_missing_and_invalid_bearer_tokens() -> None:
    missing = TestClient(prime_app).get("/api/v1/settings")
    invalid = TestClient(
        prime_app, headers={"Authorization": "Bearer wrong-token"}
    ).get("/api/v1/settings")
    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_main_api_accepts_configured_bearer_token() -> None:
    response = TestClient(prime_app, headers=HEADERS).get("/api/v1/settings")
    assert response.status_code == 200


def test_runtime_execute_rejects_missing_bearer_token() -> None:
    response = TestClient(runtime_app).post(
        "/execute", json={"task": "not-a-real-task", "payload": {}}
    )
    assert response.status_code == 401


def test_protected_api_fails_closed_when_token_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("THALOS_API_TOKEN", raising=False)
    response = TestClient(prime_app).get("/api/v1/settings")
    assert response.status_code == 503
