"""UI route tests for main and chat-first pages."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from thalos_prime.api.routes import main as main_routes
from thalos_prime.api.server import app

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


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


def test_root_ui_fallback_when_template_missing(monkeypatch: MonkeyPatch) -> None:
    """GET / serves fallback HTML when workspace template is unavailable."""
    monkeypatch.setattr(main_routes, "_UI_TEMPLATE_INDEX", Path("/tmp/thalos-missing-index.html"))
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "THALOS PRIME" in response.text
    assert "/docs" in response.text


def test_chat_ui_fallback_when_template_missing(monkeypatch: MonkeyPatch) -> None:
    """GET /chat serves fallback HTML when chat template is unavailable."""
    monkeypatch.setattr(main_routes, "_UI_TEMPLATE_CHAT", Path("/tmp/thalos-missing-chat.html"))
    with TestClient(app) as client:
        response = client.get("/chat")
    assert response.status_code == 200
    assert "THALOS PRIME CHAT" in response.text
    assert "main UI" in response.text
