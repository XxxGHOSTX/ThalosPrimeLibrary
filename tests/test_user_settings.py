"""Tests for persisted user settings schema and API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from thalos_prime.api.server import app
from thalos_prime.user_settings import (
    UserSettingsError,
    load_settings,
    reset_settings,
    settings_file_path,
    update_settings,
)


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


# ---------------------------------------------------------------------------
# Validation error paths
# ---------------------------------------------------------------------------

def test_update_settings_invalid_nav_order_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty nav_order raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="must not be empty"):
        update_settings({"workspace": {"nav_order": []}})


def test_update_settings_invalid_nav_order_unknown_view(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """nav_order with unknown view raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="unknown views"):
        update_settings({"workspace": {"nav_order": ["unknown_view_xyz"]}})


def test_update_settings_runtime_not_dict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-dict runtime raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="runtime must be an object"):
        update_settings({"runtime": "not-a-dict"})


def test_update_settings_invalid_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty host raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="non-empty string"):
        update_settings({"runtime": {"host": "", "port": 8000, "log_level": "INFO", "auto_open_browser": True}})


def test_update_settings_invalid_port(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Port out of range raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="integer in"):
        update_settings({"runtime": {"host": "127.0.0.1", "port": 99999, "log_level": "INFO", "auto_open_browser": True}})


def test_update_settings_invalid_log_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown log_level raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="log_level must be one of"):
        update_settings({"runtime": {"host": "127.0.0.1", "port": 8000, "log_level": "VERBOSE", "auto_open_browser": True}})


def test_update_settings_invalid_auto_open_browser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-bool auto_open_browser raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="must be boolean"):
        update_settings({"runtime": {"host": "127.0.0.1", "port": 8000, "log_level": "INFO", "auto_open_browser": "yes"}})


def test_update_settings_workspace_not_dict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-dict workspace raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="workspace must be an object"):
        update_settings({"workspace": "bad"})


def test_update_settings_invalid_layout_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid layout_mode raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="layout_mode must be"):
        update_settings({"workspace": {"layout_mode": "diagonal"}})


def test_update_settings_invalid_toolbar_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid toolbar_mode raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="toolbar_mode must be"):
        update_settings({"workspace": {"toolbar_mode": "floating"}})


def test_update_settings_invalid_sidebar_width(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """sidebar_width out of range raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="sidebar_width must be"):
        update_settings({"workspace": {"sidebar_width": 50}})


def test_update_settings_unsupported_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unsupported top-level key raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    with pytest.raises(UserSettingsError, match="Unsupported settings key"):
        update_settings({"unsupported_key": "value"})


def test_load_settings_schema_version_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mismatched schema_version in persisted file raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    settings_dir = tmp_path
    settings_dir.mkdir(parents=True, exist_ok=True)
    bad_data = {
        "schema_version": 999,
        "runtime": {"host": "127.0.0.1", "port": 8000, "log_level": "INFO", "auto_open_browser": True},
        "workspace": {"layout_mode": "both", "toolbar_mode": "both", "nav_order": ["console", "search", "generate", "enumerate", "decode", "history", "settings", "docs"], "sidebar_width": 250},
    }
    settings_file = settings_dir / "settings.json"
    settings_file.write_text(json.dumps(bad_data), encoding="utf-8")
    with pytest.raises(UserSettingsError, match="schema_version must be"):
        load_settings()


def test_load_settings_invalid_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Corrupt settings JSON raises UserSettingsError."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    # Create the settings dir and write corrupt JSON
    settings_dir = tmp_path
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_file = settings_dir / "settings.json"
    settings_file.write_text("{ invalid json }", encoding="utf-8")
    with pytest.raises(UserSettingsError, match="Invalid settings JSON"):
        load_settings()


def test_update_settings_empty_updates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty updates dict returns current settings unchanged."""
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    original = load_settings()
    result = update_settings({})
    assert result.runtime.port == original.runtime.port
    assert result.workspace.layout_mode == original.workspace.layout_mode
