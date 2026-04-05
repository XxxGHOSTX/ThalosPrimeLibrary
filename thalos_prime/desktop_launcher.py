"""Desktop launcher entry point for packaged Windows installation."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import uvicorn

from thalos_prime.api.server import app
from thalos_prime.user_settings import (
    RuntimeSettings,
    UserSettingsError,
    ensure_settings_dir,
    load_settings,
    runtime_data_dir,
    settings_file_path,
)

_ENV_FILENAME = ".env"


def _status_up(host: str, port: int) -> bool:
    req = Request(f"http://{host}:{port}/api/v1/status", method="GET")
    try:
        with urlopen(req, timeout=1.0) as response:
            return 200 <= response.status < 300
    except URLError:
        return False


def _ensure_runtime_files(runtime: RuntimeSettings) -> None:
    settings_dir = ensure_settings_dir()
    runtime_data_dir().mkdir(parents=True, exist_ok=True)
    env_path = settings_dir / _ENV_FILENAME
    if not env_path.exists():
        env_path.write_text(
            "\n".join(
                [
                    f"THALOS_LIBRARY_PATH={runtime_data_dir()}",
                    f"THALOS_LOG_LEVEL={runtime.log_level}",
                    "",
                ],
            ),
            encoding="utf-8",
        )
    os.environ.setdefault("THALOS_LIBRARY_PATH", str(runtime_data_dir()))
    os.environ.setdefault("THALOS_LOG_LEVEL", runtime.log_level)


def _spawn_server(runtime: RuntimeSettings) -> None:
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        subprocess.Popen(
            [
                sys.executable,
                "--serve",
                "--host",
                runtime.host,
                "--port",
                str(runtime.port),
                "--log-level",
                runtime.log_level,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        return
    subprocess.Popen(
        [
            sys.executable,
            "--serve",
            "--host",
            runtime.host,
            "--port",
            str(runtime.port),
            "--log-level",
            runtime.log_level,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _open_ui(runtime: RuntimeSettings) -> None:
    webbrowser.open(f"http://{runtime.host}:{runtime.port}/")


def _wait_until_ready(runtime: RuntimeSettings, timeout_s: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _status_up(runtime.host, runtime.port):
            return True
        time.sleep(0.25)
    return False


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="thalos-desktop")
    parser.add_argument("--serve", action="store_true", help="Serve backend API in foreground.")
    parser.add_argument("--host", default="", help="Override runtime host.")
    parser.add_argument("--port", type=int, default=0, help="Override runtime port.")
    parser.add_argument(
        "--log-level",
        default="",
        choices=["", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Override runtime log level.",
    )
    return parser


def main() -> None:
    """Desktop launch entrypoint."""
    args = _build_parser().parse_args()
    try:
        settings = load_settings()
    except UserSettingsError as exc:
        msg = f"Settings validation failed: {exc}"
        raise SystemExit(msg) from exc

    runtime = settings.runtime
    if args.host:
        runtime = RuntimeSettings(
            host=args.host,
            port=runtime.port,
            log_level=runtime.log_level,
            auto_open_browser=runtime.auto_open_browser,
        )
    if args.port:
        runtime = RuntimeSettings(
            host=runtime.host,
            port=args.port,
            log_level=runtime.log_level,
            auto_open_browser=runtime.auto_open_browser,
        )
    if args.log_level:
        runtime = RuntimeSettings(
            host=runtime.host,
            port=runtime.port,
            log_level=args.log_level,
            auto_open_browser=runtime.auto_open_browser,
        )

    _ensure_runtime_files(runtime)
    os.environ["THALOS_USER_CONFIG_DIR"] = str(settings_file_path().parent)

    if args.serve:
        uvicorn.run(
            app,
            host=runtime.host,
            port=runtime.port,
            log_level=runtime.log_level.lower(),
        )
        return

    if not _status_up(runtime.host, runtime.port):
        _spawn_server(runtime)
        if not _wait_until_ready(runtime):
            msg = "Thalos Prime failed to start within timeout."
            raise SystemExit(msg)

    if runtime.auto_open_browser:
        _open_ui(runtime)


if __name__ == "__main__":
    main()
