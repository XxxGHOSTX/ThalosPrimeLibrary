"""Tests for persisted user settings schema and API."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from thalos_prime.api.server import app
from thalos_prime.user_settings import (
    load_settings,
    reset_settings,
    settings_file_path,
    update_settings,
)

if TYPE_CHECKING:
    import pytest


def test_load_settings_creates_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    settings = load_settings()
    assert settings.runtime.host == "127.0.0.1"
    assert settings.runtime.port == 8000
    assert settings.workspace.layout_mode == "both"
    assert settings_file_path().exists()


def test_update_settings_workspace_and_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    updated = update_settings(
        {
            "runtime": {"host": "127.0.0.1", "port": 8111, "log_level": "DEBUG", "auto_open_browser": True},
            "workspace": {"layout_mode": "top", "toolbar_mode": "top", "nav_order": ["search", "console"], "sidebar_width": 260},
        },
    )
    assert updated.runtime.port == 8111
    assert updated.runtime.log_level == "DEBUG"
    assert updated.workspace.layout_mode == "top"
    assert updated.workspace.nav_order[0] == "search"
    assert "docs" in updated.workspace.nav_order


def test_reset_settings_restores_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    update_settings({"runtime": {"host": "127.0.0.1", "port": 8111, "log_level": "ERROR", "auto_open_browser": False}})
    reset = reset_settings()
    assert reset.runtime.port == 8000
    assert reset.runtime.log_level == "INFO"
    assert reset.runtime.auto_open_browser is True


def test_settings_api_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with TestClient(app) as client:
        get_resp = client.get("/api/v1/settings")
        assert get_resp.status_code == 200
        patch_resp = client.patch(
            "/api/v1/settings",
            json={
                "workspace": {
                    "layout_mode": "side",
                    "toolbar_mode": "side",
                    "nav_order": ["decode", "console"],
                    "sidebar_width": 280,
                },
            },
        )
        assert patch_resp.status_code == 200
        body = patch_resp.json()
        assert body["workspace"]["layout_mode"] == "side"
        reset_resp = client.post("/api/v1/settings/reset")
        assert reset_resp.status_code == 200
        assert reset_resp.json()["workspace"]["layout_mode"] == "both"
