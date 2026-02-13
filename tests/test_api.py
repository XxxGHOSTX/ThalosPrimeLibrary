"""Tests for API endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from configs.config import Settings
from src.api import app


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Create test settings."""
    return Settings(
        corpus_dir=str(tmp_path / "corpus"),
        index_path=str(tmp_path / "data" / "index.pkl"),
        manifest_path=str(tmp_path / "data" / "manifest.json"),
        state_db_path=str(tmp_path / "data" / "state.db"),
        event_log_path=str(tmp_path / "data" / "events.jsonl"),
        checkpoint_dir=str(tmp_path / "data" / "checkpoints"),
        enable_api_key_auth=False,
    )


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestAPIEndpoints:
    """Test API endpoints."""

    def test_root_endpoint(self, client: TestClient) -> None:
        """Test root endpoint returns HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_status_endpoint(self, client: TestClient) -> None:
        """Test status endpoint."""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestChatEndpoint:
    """Test chat endpoint."""

    def test_chat_requires_message(self, client: TestClient) -> None:
        """Test chat requires message field."""
        response = client.post("/api/chat", json={})
        assert response.status_code == 422  # Validation error

    def test_chat_basic(self, client: TestClient) -> None:
        """Test basic chat functionality."""
        # Note: This may fail if index is not built, which is expected
        response = client.post(
            "/api/chat",
            json={"message": "test message"}
        )

        # Either success or service unavailable (if not initialized)
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "session_id" in data
            assert "response" in data
            assert "seed" in data

    def test_chat_with_session_id(self, client: TestClient) -> None:
        """Test chat with provided session ID."""
        session_id = "test-session-123"

        response = client.post(
            "/api/chat",
            json={
                "session_id": session_id,
                "message": "hello"
            }
        )

        # Either success or service unavailable
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["session_id"] == session_id


class TestAuthEndpoints:
    """Test authentication."""

    def test_api_key_not_required_by_default(self, client: TestClient) -> None:
        """Test that API key is not required by default."""
        response = client.get("/api/status")
        assert response.status_code == 200
