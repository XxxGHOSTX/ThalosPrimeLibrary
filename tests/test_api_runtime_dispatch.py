"""Tests for RuntimeEngine-dispatched API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from thalos_prime.api.server import app


def test_chat_endpoint_dispatches_runtime_task() -> None:
    """POST /api/v1/chat returns ChatResponse from chat task execution (generative mode)."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "hello",
                "mode": "generative",
                "max_results": 2,
                "min_score": 80.0,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["reply"], str)
    assert body["metadata"]["task"] == "chat.v1.handle_message"
    assert "results" in body


def test_chat_endpoint_enforces_threshold_with_local_mode() -> None:
    """POST /api/v1/chat raises 422 when local mode cannot meet min_score=80."""
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
    body = response.json()
    detail = body["detail"]
    assert detail["error"] == "CoherenceThresholdError"
    assert "min_score" in detail["state_snapshot"]
    assert "checkpoint" in detail["state_snapshot"]


def test_high_coherence_endpoint_returns_contract_metadata() -> None:
    """POST /api/v1/chat/high_coherence succeeds with generative mode."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/high_coherence?min_score=80",
            json={
                "message": "hello",
                "mode": "generative",
                "max_results": 2,
            },
        )
    assert response.status_code == 200
    body = response.json()
    metadata = body["metadata"]
    assert metadata["task"] == "chat.v1.handle_message_high_coherence"
    assert metadata["min_score_target"] == 80.0
    assert metadata["high_coherence_satisfied"] is True
    assert isinstance(metadata["attempts"], int)


def test_high_coherence_endpoint_raises_422_on_threshold_miss() -> None:
    """POST /api/v1/chat/high_coherence raises 422 when local mode can't hit min_score."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/high_coherence?min_score=95",
            json={
                "message": "hello",
                "mode": "local",
                "max_results": 2,
            },
        )
    assert response.status_code == 422
    body = response.json()
    detail = body["detail"]
    assert detail["error"] == "CoherenceThresholdError"


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

