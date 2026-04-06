"""Tests for desktop launcher behavior."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pytest

import thalos_prime.desktop_launcher as launcher
from thalos_prime.user_settings import RuntimeSettings, default_settings


def _parser_for(
    *,
    serve: bool = False,
    host: str = "",
    port: int = 0,
    log_level: str = "",
) -> object:
    class _FixedParser:
        def parse_args(self) -> argparse.Namespace:
            return argparse.Namespace(
                serve=serve,
                host=host,
                port=port,
                log_level=log_level,
            )

    return _FixedParser()


def _status_false(_host: str, _port: int) -> bool:
    return False


def _ready_true(_runtime: RuntimeSettings, _timeout_s: float = 20.0) -> bool:
    return True


def _ready_false(_runtime: RuntimeSettings, _timeout_s: float = 20.0) -> bool:
    return False


def _build_parser_default() -> object:
    return _parser_for()


def _build_parser_serve() -> object:
    return _parser_for(serve=True)


def _noop_spawn(_runtime: RuntimeSettings) -> None:
    return None


def test_ensure_runtime_files_creates_env_and_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    runtime = RuntimeSettings(host="127.0.0.1", port=8000, log_level="INFO", auto_open_browser=True)
    launcher._ensure_runtime_files(runtime)
    env_file = tmp_path / ".env"
    assert env_file.exists()
    assert "THALOS_LOG_LEVEL=INFO" in env_file.read_text(encoding="utf-8")
    assert (tmp_path / "data").exists()


def test_main_desktop_spawns_and_opens_when_not_running(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("THALOS_USER_CONFIG_DIR", str(tmp_path))
    settings = default_settings()
    calls: dict[str, int] = {"spawn": 0, "open": 0}
    def _count_spawn(_runtime: RuntimeSettings) -> None:
        calls["spawn"] += 1

    def _count_open(_runtime: RuntimeSettings) -> None:
        calls["open"] += 1

    monkeypatch.setattr(launcher, "_status_up", _status_false)
    monkeypatch.setattr(launcher, "_wait_until_ready", _ready_true)
    monkeypatch.setattr(launcher, "_spawn_server", _count_spawn)
    monkeypatch.setattr(launcher, "_open_ui", _count_open)
    monkeypatch.setattr(launcher, "load_settings", lambda: settings)
    monkeypatch.setattr(launcher, "_build_parser", _build_parser_default)

    launcher.main()

    assert calls["spawn"] == 1
    assert calls["open"] == 1


def test_main_serve_invokes_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = default_settings()
    captured: dict[str, object] = {}
    def _capture_run(
        app: Any,
        host: str,
        port: int,
        log_level: str,
    ) -> None:
        del app
        captured.update({"host": host, "port": port, "log_level": log_level})

    monkeypatch.setattr(launcher, "load_settings", lambda: settings)
    monkeypatch.setattr("uvicorn.run", _capture_run)
    monkeypatch.setattr(launcher, "_build_parser", _build_parser_serve)
    launcher.main()
    assert captured["host"] == settings.runtime.host
    assert captured["port"] == settings.runtime.port
    assert captured["log_level"] == settings.runtime.log_level.lower()


def test_main_raises_on_start_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = default_settings()
    monkeypatch.setattr(launcher, "load_settings", lambda: settings)
    monkeypatch.setattr(launcher, "_status_up", _status_false)
    monkeypatch.setattr(launcher, "_spawn_server", _noop_spawn)
    monkeypatch.setattr(launcher, "_wait_until_ready", _ready_false)
    monkeypatch.setattr(launcher, "_build_parser", _build_parser_default)
    with pytest.raises(SystemExit, match="failed to start"):
        launcher.main()
