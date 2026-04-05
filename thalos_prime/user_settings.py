"""User settings and runtime configuration persistence for Thalos Prime.

Settings are stored per-user in a writable configuration directory (AppData on
Windows, ~/.config elsewhere).  The schema is validated on every read/update.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

LayoutMode = Literal["side", "top", "both"]
ToolbarMode = Literal["top", "side", "both", "none"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_SETTINGS_FILENAME = "settings.json"
_SCHEMA_VERSION = 1
_DEFAULT_NAV_ORDER = [
    "console",
    "search",
    "generate",
    "enumerate",
    "decode",
    "history",
    "settings",
    "docs",
]
_VALID_NAV_VIEWS = set(_DEFAULT_NAV_ORDER)


class UserSettingsError(ValueError):
    """Raised when settings content is invalid."""


@dataclass(frozen=True)
class RuntimeSettings:
    """Runtime startup settings."""

    host: str = "127.0.0.1"
    port: int = 8000
    log_level: LogLevel = "INFO"
    auto_open_browser: bool = True


@dataclass(frozen=True)
class WorkspaceSettings:
    """UI layout/workspace settings."""

    layout_mode: LayoutMode = "both"
    toolbar_mode: ToolbarMode = "both"
    nav_order: list[str] = field(default_factory=lambda: list(_DEFAULT_NAV_ORDER))
    sidebar_width: int = 250


@dataclass(frozen=True)
class UserSettings:
    """Top-level persisted settings."""

    schema_version: int = _SCHEMA_VERSION
    runtime: RuntimeSettings = field(default_factory=RuntimeSettings)
    workspace: WorkspaceSettings = field(default_factory=WorkspaceSettings)


def _settings_root_dir() -> Path:
    configured = os.getenv("THALOS_USER_CONFIG_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt":
        app_data = os.getenv("LOCALAPPDATA")
        if app_data:
            return Path(app_data).resolve() / "ThalosPrime"
    return Path.home().resolve() / ".config" / "thalos_prime"


def settings_file_path() -> Path:
    """Return the absolute path to the persisted settings file."""
    return _settings_root_dir() / _SETTINGS_FILENAME


def runtime_data_dir() -> Path:
    """Return per-user writable runtime data directory."""
    return _settings_root_dir() / "data"


def ensure_settings_dir() -> Path:
    """Ensure settings directory exists and return it."""
    root = _settings_root_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _validate_nav_order(order: list[str]) -> list[str]:
    if not order:
        msg = "workspace.nav_order must not be empty"
        raise UserSettingsError(msg)
    if any(view not in _VALID_NAV_VIEWS for view in order):
        msg = "workspace.nav_order contains unknown views"
        raise UserSettingsError(msg)
    deduped = list(dict.fromkeys(order))
    missing = [view for view in _DEFAULT_NAV_ORDER if view not in deduped]
    return deduped + missing


def _coerce_runtime(payload: object) -> RuntimeSettings:
    if not isinstance(payload, dict):
        msg = "runtime must be an object"
        raise UserSettingsError(msg)
    host = payload.get("host", "127.0.0.1")
    port = payload.get("port", 8000)
    log_level = payload.get("log_level", "INFO")
    auto_open_browser = payload.get("auto_open_browser", True)
    if not isinstance(host, str) or not host.strip():
        msg = "runtime.host must be a non-empty string"
        raise UserSettingsError(msg)
    if not isinstance(port, int) or not (1 <= port <= 65535):
        msg = "runtime.port must be an integer in [1, 65535]"
        raise UserSettingsError(msg)
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        msg = "runtime.log_level must be one of DEBUG/INFO/WARNING/ERROR/CRITICAL"
        raise UserSettingsError(msg)
    if not isinstance(auto_open_browser, bool):
        msg = "runtime.auto_open_browser must be boolean"
        raise UserSettingsError(msg)
    return RuntimeSettings(
        host=host.strip(),
        port=port,
        log_level=log_level,
        auto_open_browser=auto_open_browser,
    )


def _coerce_workspace(payload: object) -> WorkspaceSettings:
    if not isinstance(payload, dict):
        msg = "workspace must be an object"
        raise UserSettingsError(msg)
    layout_mode = payload.get("layout_mode", "both")
    toolbar_mode = payload.get("toolbar_mode", "both")
    nav_order = payload.get("nav_order", list(_DEFAULT_NAV_ORDER))
    sidebar_width = payload.get("sidebar_width", 250)
    if layout_mode not in {"side", "top", "both"}:
        msg = "workspace.layout_mode must be one of side/top/both"
        raise UserSettingsError(msg)
    if toolbar_mode not in {"top", "side", "both", "none"}:
        msg = "workspace.toolbar_mode must be one of top/side/both/none"
        raise UserSettingsError(msg)
    if not isinstance(nav_order, list) or not all(isinstance(v, str) for v in nav_order):
        msg = "workspace.nav_order must be a list of strings"
        raise UserSettingsError(msg)
    if not isinstance(sidebar_width, int) or not (180 <= sidebar_width <= 480):
        msg = "workspace.sidebar_width must be an integer in [180, 480]"
        raise UserSettingsError(msg)
    return WorkspaceSettings(
        layout_mode=layout_mode,
        toolbar_mode=toolbar_mode,
        nav_order=_validate_nav_order(nav_order),
        sidebar_width=sidebar_width,
    )


def _coerce_user_settings(payload: object) -> UserSettings:
    if not isinstance(payload, dict):
        msg = "settings payload must be an object"
        raise UserSettingsError(msg)
    schema_version = payload.get("schema_version", _SCHEMA_VERSION)
    if schema_version != _SCHEMA_VERSION:
        msg = f"schema_version must be {_SCHEMA_VERSION}"
        raise UserSettingsError(msg)
    runtime = _coerce_runtime(payload.get("runtime", {}))
    workspace = _coerce_workspace(payload.get("workspace", {}))
    return UserSettings(
        schema_version=schema_version,
        runtime=runtime,
        workspace=workspace,
    )


def _merge_settings(base: UserSettings, updates: dict[str, object]) -> UserSettings:
    if not updates:
        return base
    merged: dict[str, object] = asdict(base)
    for key in updates:
        if key not in {"runtime", "workspace"}:
            msg = f"Unsupported settings key: {key}"
            raise UserSettingsError(msg)
    for key, value in updates.items():
        merged[key] = value
    return _coerce_user_settings(merged)


def write_settings(settings: UserSettings) -> None:
    """Atomically write settings to disk."""
    ensure_settings_dir()
    settings_path = settings_file_path()
    tmp_path = settings_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(asdict(settings), indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(settings_path)


def default_settings() -> UserSettings:
    """Return default settings object."""
    return UserSettings()


def load_settings() -> UserSettings:
    """Load settings from disk, creating defaults if absent."""
    ensure_settings_dir()
    settings_path = settings_file_path()
    if not settings_path.exists():
        settings = default_settings()
        write_settings(settings)
        return settings
    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"Invalid settings JSON: {exc}"
        raise UserSettingsError(msg) from exc
    settings = _coerce_user_settings(payload)
    write_settings(settings)
    return settings


def update_settings(updates: dict[str, object]) -> UserSettings:
    """Merge partial updates into current settings and persist."""
    current = load_settings()
    merged = _merge_settings(current, updates)
    write_settings(merged)
    return merged


def reset_settings() -> UserSettings:
    """Reset settings to defaults and persist."""
    settings = default_settings()
    write_settings(settings)
    return settings
