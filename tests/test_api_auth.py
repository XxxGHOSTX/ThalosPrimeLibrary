"""Regression tests for authentication boundaries on protected APIs."""

from fastapi.testclient import TestClient

from thalos_prime.api.server import app as prime_app, create_app
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



def test_authentication_bypass_requires_explicit_development(monkeypatch) -> None:
    """An explicitly local development environment may use the local UI bypass."""
    monkeypatch.setenv("THALOS_ENV", "development")
    monkeypatch.setenv("THALOS_AUTH_DISABLED", "1")
    monkeypatch.delenv("THALOS_API_TOKEN", raising=False)
    response = TestClient(prime_app).get("/api/v1/settings")
    assert response.status_code == 200


def test_authentication_bypass_is_rejected_in_production(monkeypatch) -> None:
    """Setting the bypass flag in production must fail closed."""
    monkeypatch.setenv("THALOS_ENV", "production")
    monkeypatch.setenv("THALOS_AUTH_DISABLED", "1")
    response = TestClient(prime_app).get("/api/v1/settings")
    assert response.status_code == 503


def test_authentication_bypass_is_rejected_when_environment_is_unknown(monkeypatch) -> None:
    """The bypass is not enabled when the deployment mode is absent or unknown."""
    monkeypatch.delenv("THALOS_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("THALOS_AUTH_DISABLED", "1")
    response = TestClient(prime_app).get("/api/v1/settings")
    assert response.status_code == 503



def test_production_disables_interactive_api_documentation(monkeypatch) -> None:
    """Swagger, ReDoc, and OpenAPI are not exposed by the production app."""
    monkeypatch.setenv("THALOS_ENV", "production")
    monkeypatch.setenv("THALOS_CORS_ORIGINS", "https://app.example.test")
    production_app = create_app()
    assert production_app.docs_url is None
    assert production_app.redoc_url is None
    assert production_app.openapi_url is None



def test_main_api_status_requires_bearer_token(monkeypatch) -> None:
    """The root UI remains public, but the API status endpoint requires auth."""
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)
    monkeypatch.setenv("THALOS_API_TOKEN", "test-api-token-for-status-route-only-32")
    client = TestClient(prime_app)
    assert client.get("/").status_code == 200
    assert client.get("/api/v1/status").status_code == 401
    assert client.get(
        "/api/v1/status",
        headers={"Authorization": "Bearer test-api-token-for-status-route-only-32"},
    ).status_code == 200
