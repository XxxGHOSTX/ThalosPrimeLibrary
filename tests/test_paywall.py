"""Tests for the paywall auth and subscription routes.

Covers user registration, login, token verification,
subscription tier management, and PayPal order creation endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from thalos_prime.api.routes.auth import _TOKENS, _USERS, _hash_password


def _make_client() -> TestClient:
    """Create a FastAPI test client for the Thalos Prime app.

    Returns:
        Configured TestClient instance.

    """
    from thalos_prime.api.server import create_app

    app = create_app()
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def clear_user_store() -> None:
    """Reset in-memory user and token stores before each test."""
    _USERS.clear()
    _TOKENS.clear()


class TestRegister:
    """Tests for POST /api/v1/auth/register."""

    def test_register_success(self) -> None:
        """Registers a new user and returns 201 with user details."""
        client = _make_client()
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "testuser", "email": "test@example.com", "password": "securepass"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "user_id" in data

    def test_register_duplicate_username(self) -> None:
        """Returns 409 when username is already taken."""
        client = _make_client()
        client.post(
            "/api/v1/auth/register",
            json={"username": "dup", "email": "a@example.com", "password": "password123"},
        )
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "dup", "email": "b@example.com", "password": "password123"},
        )
        assert resp.status_code == 409

    def test_register_duplicate_email(self) -> None:
        """Returns 409 when email is already registered."""
        client = _make_client()
        client.post(
            "/api/v1/auth/register",
            json={"username": "user1", "email": "shared@example.com", "password": "password123"},
        )
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "user2", "email": "shared@example.com", "password": "password123"},
        )
        assert resp.status_code == 409


class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    def _register(self, client: TestClient, username: str = "user", pw: str = "mypassword") -> None:
        client.post(
            "/api/v1/auth/register",
            json={"username": username, "email": f"{username}@example.com", "password": pw},
        )

    def test_login_success(self) -> None:
        """Returns 200 with bearer token on valid credentials."""
        client = _make_client()
        self._register(client)
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "user", "password": "mypassword"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["token_type"] == "bearer"  # noqa: S105 - "bearer" is the RFC 6750 token type, not a password
        assert "access_token" in data
        assert len(data["access_token"]) > 0
        assert data["username"] == "user"
        assert data["subscription_tier"] == "free"

    def test_login_wrong_password(self) -> None:
        """Returns 401 on incorrect password."""
        client = _make_client()
        self._register(client)
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "user", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    def test_login_unknown_user(self) -> None:
        """Returns 401 for unknown username."""
        client = _make_client()
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "ghost", "password": "anypass"},
        )
        assert resp.status_code == 401


class TestGetProfile:
    """Tests for GET /api/v1/auth/me."""

    def test_get_profile_authenticated(self) -> None:
        """Returns user profile for authenticated request."""
        client = _make_client()
        client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "testpass1"},
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "testpass1"},
        )
        token = login_resp.json()["access_token"]
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "alice"
        assert data["subscription_tier"] == "free"

    def test_get_profile_unauthenticated(self) -> None:
        """Returns 401 without token."""
        client = _make_client()
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_get_profile_invalid_token(self) -> None:
        """Returns 401 with invalid token."""
        client = _make_client()
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert resp.status_code == 401


class TestLogout:
    """Tests for POST /api/v1/auth/logout."""

    def test_logout_success(self) -> None:
        """Invalidates token on logout."""
        client = _make_client()
        client.post(
            "/api/v1/auth/register",
            json={"username": "bob", "email": "bob@example.com", "password": "bobpass12"},
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "bob", "password": "bobpass12"},
        )
        token = login_resp.json()["access_token"]

        # Logout
        resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        # Token should now be invalid
        profile_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert profile_resp.status_code == 401


class TestSubscriptionStatus:
    """Tests for GET /api/v1/subscription/status."""

    def _register_and_login(self, client: TestClient) -> str:
        client.post(
            "/api/v1/auth/register",
            json={"username": "subuser", "email": "sub@example.com", "password": "subpassword"},
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "subuser", "password": "subpassword"},
        )
        return str(login_resp.json()["access_token"])

    def test_subscription_status_free(self) -> None:
        """New users default to free tier subscription status."""
        client = _make_client()
        token = self._register_and_login(client)
        resp = client.get(
            "/api/v1/subscription/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "free"
        assert data["is_active"] is True
        assert "basic_search" in data["features"]

    def test_subscription_status_unauthenticated(self) -> None:
        """Returns 401 without valid token."""
        client = _make_client()
        resp = client.get("/api/v1/subscription/status")
        assert resp.status_code == 401


class TestSubscriptionFeatures:
    """Tests for GET /api/v1/auth/subscription-features."""

    def test_subscription_features(self) -> None:
        """Returns tier descriptions with features and pricing."""
        client = _make_client()
        resp = client.get("/api/v1/auth/subscription-features")
        assert resp.status_code == 200
        data = resp.json()
        assert "tiers" in data
        assert "free" in data["tiers"]
        assert "pro" in data["tiers"]
        assert "enterprise" in data["tiers"]
        assert data["tiers"]["pro"]["price_usd"] == "9.99"
        assert "unlimited_search" in data["tiers"]["pro"]["features"]


class TestHashPassword:
    """Unit tests for internal _hash_password function."""

    def test_deterministic(self) -> None:
        """Same password always produces the same hash."""
        h1 = _hash_password("mypassword")
        h2 = _hash_password("mypassword")
        assert h1 == h2

    def test_different_passwords(self) -> None:
        """Different passwords produce different hashes."""
        h1 = _hash_password("password1")
        h2 = _hash_password("password2")
        assert h1 != h2
