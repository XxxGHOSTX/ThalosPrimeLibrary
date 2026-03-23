"""Tests for RuntimeEngine-dispatched API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from thalos_prime.api.server import app


def test_chat_endpoint_dispatches_runtime_task() -> None:
    """POST /api/v1/chat returns ChatResponse from chat task execution."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "hello",
                "mode": "local",
                "max_results": 2,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["reply"], str)
    assert body["metadata"]["task"] == "chat.v1.handle_message"
    assert "results" in body


def test_high_coherence_endpoint_returns_contract_metadata() -> None:
    """POST /api/v1/chat/high_coherence includes high-coherence metadata keys."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/high_coherence?min_score=51",
            json={
                "message": "hello",
                "mode": "local",
                "max_results": 2,
            },
        )
    assert response.status_code == 200
    body = response.json()
    metadata = body["metadata"]
    assert metadata["task"] == "chat.v1.handle_message_high_coherence"
    assert metadata["min_score_target"] == 51.0
    assert isinstance(metadata["high_coherence_satisfied"], bool)
    assert isinstance(metadata["fallback_used"], bool)
    assert isinstance(metadata["attempts"], int)


def test_admin_tasks_lists_registered_task_names() -> None:
    """GET /api/v1/admin/tasks returns the RuntimeEngine registered tasks."""
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/admin/tasks",
            headers={"x-api-key": "admin-key-change-in-production"},
        )
    assert response.status_code == 200
    body = response.json()
    tasks = set(body["tasks"])
    assert "chat.v1.handle_message" in tasks
    assert "chat.v1.handle_message_high_coherence" in tasks
    assert "search.v1.query" in tasks
    assert "babel.v1.generate" in tasks
    assert "babel.v1.enumerate" in tasks
    assert "babel.v1.decode" in tasks

