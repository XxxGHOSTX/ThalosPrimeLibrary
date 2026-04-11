#!/usr/bin/env python3
"""Thalos Prime program launcher.

Provides a full launcher for starting, stopping, restarting, and monitoring
the Thalos Prime API server with deterministic process management.
"""

from __future__ import annotations

import argparse
import importlib
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Final

APP_IMPORT: Final[str] = "thalos_prime.api.server:app"
DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8000

WORKSPACE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = WORKSPACE_ROOT / ".thalos_runtime"
PID_FILE: Final[Path] = RUNTIME_DIR / "api.pid"
LOG_FILE: Final[Path] = RUNTIME_DIR / "api.log"
REQUIRED_MODULES: Final[tuple[str, ...]] = ("uvicorn", "fastapi", "pydantic")


class LauncherError(RuntimeError):
    """Raised for launcher-level errors."""


def _ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    text = PID_FILE.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _write_pid(pid: int) -> None:
    _ensure_runtime_dir()
    PID_FILE.write_text(f"{pid}\n", encoding="utf-8")


def _remove_pid_file() -> None:
    if PID_FILE.exists():
        PID_FILE.unlink()


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _terminate_pid(pid: int, timeout: float = 8.0) -> bool:
    if not _pid_exists(pid):
        return True

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_exists(pid):
            return True
        time.sleep(0.2)

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return True

    time.sleep(0.2)
    return not _pid_exists(pid)


def _build_uvicorn_command(host: str, port: int, reload_enabled: bool) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        APP_IMPORT,
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        "info",
    ]
    if reload_enabled:
        command.append("--reload")
    return command


def _wait_until_ready(host: str, port: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _is_port_open(host, port):
            return True
        time.sleep(0.2)
    return False


def _http_ready(url: str, timeout: float = 2.0) -> bool:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            status_code = getattr(response, "status", 0)
            return 200 <= int(status_code) < 500
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def _server_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _docs_url(host: str, port: int) -> str:
    return f"{_server_url(host, port)}/docs"


def command_status(host: str, port: int) -> int:
    pid = _read_pid()
    listening = _is_port_open(host, port)

    if pid is None:
        print(f"PID file: missing ({PID_FILE})")
    else:
        print(f"PID file: {pid}")

    if pid is not None and _pid_exists(pid):
        print("Process: running")
    elif pid is not None:
        print("Process: not running (stale pid file)")
    else:
        print("Process: unknown")

    print(f"Port {port}: {'open' if listening else 'closed'}")
    print(f"Docs URL: {_docs_url(host, port)}")
    print(f"Docs reachable: {'yes' if _http_ready(_docs_url(host, port)) else 'no'}")
    print(f"Log file: {LOG_FILE}")

    return 0 if listening else 1


def command_stop(_host: str, _port: int) -> int:
    pid = _read_pid()
    if pid is None:
        print("No PID file found; nothing to stop.")
        return 0

    if _terminate_pid(pid):
        _remove_pid_file()
        print(f"Stopped server process {pid}.")
        return 0

    raise LauncherError(f"Failed to stop server process {pid}.")


def command_start(host: str, port: int, *, background: bool, reload_enabled: bool, open_browser: bool) -> int:
    _ensure_runtime_dir()

    pid = _read_pid()
    if pid is not None and not _pid_exists(pid):
        _remove_pid_file()
        pid = None

    if pid is not None and _pid_exists(pid):
        if _is_port_open(host, port):
            print(f"Server already running (pid={pid}) at {_docs_url(host, port)}")
            if open_browser:
                webbrowser.open(_docs_url(host, port))
            return 0
        raise LauncherError(
            f"PID file points to running process {pid}, but port {port} is closed. Stop or clean runtime state."
        )

    if _is_port_open(host, port):
        docs = _docs_url(host, port)
        if _http_ready(docs):
            print(f"Port {port} is already serving a healthy endpoint at {docs}.")
            if open_browser:
                webbrowser.open(docs)
            return 0
        raise LauncherError(
            f"Port {port} is already in use by another process and docs endpoint is not healthy. "
            "Stop the conflicting process or choose a different port."
        )

    command = _build_uvicorn_command(host, port, reload_enabled)

    if background:
        with LOG_FILE.open("a", encoding="utf-8") as log_handle:
            process = subprocess.Popen(  # noqa: S603
                command,
                cwd=str(WORKSPACE_ROOT),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        _write_pid(process.pid)

        if not _wait_until_ready(host, port, timeout=20.0):
            _remove_pid_file()
            raise LauncherError(
                f"Server failed to become ready. Check log: {LOG_FILE}"
            )

        print(f"Server started in background (pid={process.pid}).")
        print(f"Docs: {_docs_url(host, port)}")
        print(f"Logs: {LOG_FILE}")

        if open_browser:
            webbrowser.open(_docs_url(host, port))
        return 0

    print("Starting Thalos Prime API in foreground. Press Ctrl+C to stop.")
    print(f"Docs: {_docs_url(host, port)}")

    try:
        completed = subprocess.run(command, cwd=str(WORKSPACE_ROOT), check=False)  # noqa: S603
    finally:
        _remove_pid_file()
    return completed.returncode


def command_restart(host: str, port: int, *, background: bool, reload_enabled: bool, open_browser: bool) -> int:
    command_stop(host, port)
    return command_start(
        host,
        port,
        background=background,
        reload_enabled=reload_enabled,
        open_browser=open_browser,
    )


def command_open(host: str, port: int) -> int:
    url = _docs_url(host, port)
    webbrowser.open(url)
    print(f"Opened: {url}")
    return 0


def command_doctor() -> int:
    print("Running launcher environment checks...")

    failures: list[str] = []

    if not Path(sys.executable).exists():
        failures.append(f"Python executable not found: {sys.executable}")

    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
            print(f"[OK] Python module available: {module_name}")
        except ModuleNotFoundError:
            failures.append(f"Missing Python module: {module_name}")

    module_name, attr_name = APP_IMPORT.split(":", maxsplit=1)
    try:
        module = importlib.import_module(module_name)
        if not hasattr(module, attr_name):
            failures.append(f"App import missing attribute: {APP_IMPORT}")
        else:
            print(f"[OK] App import target resolved: {APP_IMPORT}")
    except ModuleNotFoundError:
        failures.append(f"App module not importable: {module_name}")

    _ensure_runtime_dir()
    try:
        probe_file = RUNTIME_DIR / ".write_probe"
        probe_file.write_text("ok", encoding="utf-8")
        probe_file.unlink()
        print(f"[OK] Runtime directory writable: {RUNTIME_DIR}")
    except OSError as error:
        failures.append(f"Runtime directory not writable: {RUNTIME_DIR} ({error})")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}", file=sys.stderr)
        raise LauncherError("Environment validation failed. Resolve failures and retry.")

    print("Launcher environment checks passed.")
    return 0


def command_launch(host: str, port: int, *, reload_enabled: bool) -> int:
    command_doctor()
    return command_start(
        host,
        port,
        background=True,
        reload_enabled=reload_enabled,
        open_browser=True,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Thalos Prime launcher")
    parser.add_argument(
        "command",
        choices=["launch", "doctor", "start", "stop", "restart", "status", "open"],
        nargs="?",
        default="launch",
        help="Launcher command",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port")
    parser.add_argument(
        "--background",
        action="store_true",
        help="Run server in background (default: foreground)",
    )
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload")
    parser.add_argument("--open", action="store_true", help="Open docs URL in browser")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        if args.command == "doctor":
            return command_doctor()
        if args.command == "launch":
            return command_launch(args.host, args.port, reload_enabled=args.reload)
        if args.command == "status":
            return command_status(args.host, args.port)
        if args.command == "stop":
            return command_stop(args.host, args.port)
        if args.command == "open":
            return command_open(args.host, args.port)
        if args.command == "restart":
            return command_restart(
                args.host,
                args.port,
                background=args.background,
                reload_enabled=args.reload,
                open_browser=args.open,
            )
        return command_start(
            args.host,
            args.port,
            background=args.background,
            reload_enabled=args.reload,
            open_browser=args.open,
        )
    except LauncherError as error:
        print(f"Launcher error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
