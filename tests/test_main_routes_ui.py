"""UI route tests for main and chat-first pages."""

from __future__ import annotations

from fastapi.testclient import TestClient

from thalos_prime.api.server import app


def test_root_ui_serves_workspace_template() -> None:
    """GET / returns the existing workspace UI."""
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "THALOS PRIME" in response.text
    assert "/static/js/console-handler.js" in response.text


def test_chat_ui_serves_chat_first_template() -> None:
    """GET /chat returns the chat-first UI template."""
    with TestClient(app) as client:
        response = client.get("/chat")
    assert response.status_code == 200
    assert "THALOS PRIME CHAT" in response.text
    assert "/static/js/chat-page.js" in response.text
