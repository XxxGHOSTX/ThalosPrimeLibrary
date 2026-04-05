#!/usr/bin/env python3
"""ThalosPrimeLibrary — Cross-platform launch entry point.

This is the **single file** you need to boot everything:
- Detects operating system (Windows, Linux, macOS)
- Validates Python version and required environment
- Checks and installs missing dependencies from pyproject.toml
- Loads .env configuration
- Starts the API server via `python -m thalos_prime`

Usage::

    python launch.py                          # start API server (default)
    python launch.py --action test            # run test suite
    python launch.py --action validate        # run all validators
    python launch.py --action clean           # clean build artifacts
    python launch.py --action check           # full check (lint + type + test + validate)
    python launch.py --action none            # setup only, no server

    python launch.py --host 0.0.0.0 --port 9000
    python launch.py --log-level DEBUG

Windows users: .\\setup.ps1  (PowerShell)
Unix/macOS:    bash setup.sh

Control Plane / Data Plane boundary:
- This module: Control Plane — environment validation, dependency check, dispatch.
- thalos_prime/__main__.py: Control Plane — engine init, workers, API server.
- API handlers, RuntimeEngine tasks: Data Plane.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import platform
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Logging — configured first
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("thalos_prime.launch")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MIN_PYTHON = (3, 12)
_REPO_ROOT = Path(__file__).parent.resolve()
_VENV_DIR = _REPO_ROOT / ".venv"
_ENV_FILE = _REPO_ROOT / ".env"
_ENV_EXAMPLE = _REPO_ROOT / ".env.example"
_DATA_DIR = _REPO_ROOT / "data"
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8000

_CLEAN_TARGETS = [
    "build", "dist", "*.egg-info",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "htmlcov", ".coverage",
]

_BANNER = """\
╔══════════════════════════════════════════════════════════════╗
║   ThalosPrimeLibrary — Sovereign Epistemic Operating System  ║
║   T = ⟨D, I, R, V, E, P, B_t⟩                               ║
╚══════════════════════════════════════════════════════════════╝
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section(title: str) -> None:
    bar = "─" * 60
    print(f"\n{bar}\n  {title}\n{bar}")


def _ok(msg: str) -> None:
    print(f"  ✓  {msg}")


def _step(msg: str) -> None:
    print(f"  →  {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠  {msg}", file=sys.stderr)


def _fail(msg: str) -> None:
    print(f"  ✗  {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# OS detection
# ---------------------------------------------------------------------------

def _detect_os() -> str:
    """Return a normalised OS label: 'windows', 'linux', or 'macos'."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    return "linux"


# ---------------------------------------------------------------------------
# Python version check
# ---------------------------------------------------------------------------

def _check_python() -> None:
    """Halt if Python version is below the minimum requirement."""
    vi = sys.version_info
    if (vi.major, vi.minor) < _MIN_PYTHON:
        _fail(
            f"Python {_MIN_PYTHON[0]}.{_MIN_PYTHON[1]}+ required; "
            f"found {vi.major}.{vi.minor}.{vi.micro}. "
            "Download from https://www.python.org/downloads/"
        )
    _ok(f"Python {vi.major}.{vi.minor}.{vi.micro}")


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    """Load .env into os.environ without external dependencies."""
    env_path = _ENV_FILE
    if not env_path.exists():
        if _ENV_EXAMPLE.exists():
            import shutil as _shutil
            _shutil.copy(_ENV_EXAMPLE, env_path)
            _ok(f"Created .env from .env.example")
        else:
            env_path.write_text(
                f"THALOS_LIBRARY_PATH=./data\nTHALOS_LOG_LEVEL=INFO\n",
                encoding="utf-8",
            )
            _ok("Wrote minimal .env")

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

    _ok(f".env loaded from {env_path}")


# ---------------------------------------------------------------------------
# data/ directory
# ---------------------------------------------------------------------------

def _ensure_data_dir() -> None:
    """Create the data/ directory if it does not exist."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _ok(f"data/ directory ready ({_DATA_DIR})")


# ---------------------------------------------------------------------------
# Dependency installation
# ---------------------------------------------------------------------------

def _python_executable() -> str:
    """Return the active Python executable path (venv-aware)."""
    return sys.executable


def _pip_install(extras: str = ".[dev]") -> None:
    """Install package with given extras using the current Python executable."""
    _step(f"Installing {extras} ...")
    result = subprocess.run(
        [_python_executable(), "-m", "pip", "install", "-e", extras, "--quiet"],
        capture_output=False,
        check=False,
    )
    if result.returncode != 0:
        _fail(f"pip install failed for {extras}")
    _ok(f"Installed {extras}")


def _check_imports() -> bool:
    """Return True if the core thalos_prime package is importable."""
    try:
        import thalos_prime  # noqa: F401
        return True
    except ImportError:
        return False


def _ensure_deps() -> None:
    """Install dependencies if the package is not already importable."""
    if _check_imports():
        _ok("thalos_prime already importable — skipping install")
        return
    _step("thalos_prime not importable — installing ...")
    _pip_install(".[dev]")
    if not _check_imports():
        _fail("Package installation succeeded but thalos_prime is still not importable.")


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def _clean() -> None:
    """Remove build artifacts and caches."""
    _section("Cleanup")
    import glob
    removed = 0
    for pattern in _CLEAN_TARGETS:
        for path in glob.glob(str(_REPO_ROOT / pattern), recursive=False):
            p = Path(path)
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
            removed += 1
    # __pycache__ and .pyc
    for p in _REPO_ROOT.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
        removed += 1
    for p in _REPO_ROOT.rglob("*.pyc"):
        p.unlink(missing_ok=True)
        removed += 1
    _ok(f"Removed {removed} artifact(s)")


# ---------------------------------------------------------------------------
# Environment config snapshot (for audit)
# ---------------------------------------------------------------------------

def _config_hash() -> str:
    """Return deterministic SHA-256 prefix of key environment variables."""
    keys = sorted(k for k in os.environ if k.startswith("THALOS_") or k in {"PYTHONPATH"})
    payload = "|".join(f"{k}={os.environ.get(k, '')}" for k in keys)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Action runners
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    """Execute the pytest test suite."""
    _section("Tests")
    result = subprocess.run(
        [_python_executable(), "-m", "pytest", "tests", "-v", "--tb=short"],
        cwd=str(_REPO_ROOT),
        check=False,
    )
    if result.returncode != 0:
        _fail("Tests failed — see output above.")
    _ok("All tests passed")


def _run_validate() -> None:
    """Run all custom validators."""
    _section("Validators")
    validators = [
        "tools/validate_lifecycle.py",
        "tools/validate_determinism.py",
        "tools/validate_state.py",
        "tools/validate_docs.py",
        "tools/detect_prohibited_patterns.py",
    ]
    for v in validators:
        v_path = _REPO_ROOT / v
        if not v_path.exists():
            _warn(f"Validator not found: {v} — skipping")
            continue
        _step(f"Running {v} ...")
        result = subprocess.run(
            [_python_executable(), str(v_path)],
            cwd=str(_REPO_ROOT),
            check=False,
        )
        if result.returncode != 0:
            _fail(f"Validator failed: {v}")
    _ok("All validators passed")


def _run_check() -> None:
    """Run full quality check: mypy + ruff + tests + validators."""
    _section("Full quality check")
    commands: list[list[str]] = [
        [_python_executable(), "-m", "mypy", "thalos_prime", "--strict",
         "--show-error-codes", "--no-implicit-optional"],
        [_python_executable(), "-m", "ruff", "check", "thalos_prime", "tests",
         "--select", "ALL", "--ignore", "COM812,ISC001,ANN101,ANN102,D203,D213"],
        [_python_executable(), "-m", "pytest", "tests", "-q", "--tb=short"],
    ]
    for cmd in commands:
        _step(f"{' '.join(cmd[:3])} ...")
        result = subprocess.run(cmd, cwd=str(_REPO_ROOT), check=False)
        if result.returncode != 0:
            _fail(f"Command failed: {' '.join(cmd)}")
    _run_validate()
    _ok("All checks passed ✓")


def _run_serve(host: str, port: int, log_level: str) -> None:
    """Start the API server via thalos_prime/__main__.py."""
    _section("API Server")
    print(f"  API docs  : http://{host}:{port}/docs")
    print(f"  Status    : http://{host}:{port}/api/v1/status")
    print(f"  Chat API  : http://{host}:{port}/api/v1/chat")
    print()
    print("  Press Ctrl+C to stop.")
    print()
    result = subprocess.run(
        [
            _python_executable(), "-m", "thalos_prime",
            "--host", host,
            "--port", str(port),
            "--log-level", log_level,
        ],
        cwd=str(_REPO_ROOT),
        check=False,
    )
    if result.returncode not in (0, 130):  # 130 = Ctrl+C
        _fail(f"API server exited with code {result.returncode}")


def _run_desktop() -> None:
    """Desktop launcher mode for packaged installs.

    - Ensures per-user settings/config/data are initialized.
    - Starts the API server if not running.
    - Opens the Matrix UI in the default browser.
    """
    from urllib.error import URLError
    from urllib.request import Request, urlopen

    from thalos_prime.user_settings import (
        UserSettingsError,
        load_settings,
        runtime_data_dir,
    )

    _section("Desktop Launcher")
    try:
        settings = load_settings()
    except UserSettingsError as exc:
        _fail(f"Settings validation failed: {exc}")
        return

    host = settings.runtime.host
    port = settings.runtime.port
    log_level = settings.runtime.log_level

    data_dir = runtime_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("THALOS_LIBRARY_PATH", str(data_dir))

    status_url = f"http://{host}:{port}/api/v1/status"
    req = Request(status_url, method="GET")
    running = False
    try:
        with urlopen(req, timeout=1.0) as response:
            running = 200 <= response.status < 300
    except URLError:
        running = False

    if not running:
        _step("Starting Thalos Prime backend in detached mode ...")
        if platform.system().lower() == "windows":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            subprocess.Popen(
                [
                    _python_executable(),
                    "-m",
                    "thalos_prime",
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--log-level",
                    log_level,
                ],
                cwd=str(_REPO_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        else:
            subprocess.Popen(
                [
                    _python_executable(),
                    "-m",
                    "thalos_prime",
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--log-level",
                    log_level,
                ],
                cwd=str(_REPO_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

    ui_url = f"http://{host}:{port}/"
    if settings.runtime.auto_open_browser:
        _step(f"Opening UI: {ui_url}")
        webbrowser.open(ui_url)
    _ok("Desktop launch complete")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="launch.py",
        description=(
            "ThalosPrimeLibrary — cross-platform launcher. "
            "Sets up the environment and runs the requested action."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python launch.py                      # setup + serve (default)\n"
            "  python launch.py --action test         # run tests\n"
            "  python launch.py --action validate     # run validators\n"
            "  python launch.py --action check        # full quality check\n"
            "  python launch.py --action clean        # clean build artifacts\n"
            "  python launch.py --action none         # setup only\n"
            "\n"
            "Windows: .\\setup.ps1\n"
            "Unix:    bash setup.sh\n"
        ),
    )
    parser.add_argument(
        "--action",
        default="serve",
        choices=["serve", "test", "validate", "check", "clean", "none"],
        help="Action to perform after setup (default: serve).",
    )
    parser.add_argument("--host", default=_DEFAULT_HOST, help="API server bind host.")
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT, help="API server bind port.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity (default: INFO).",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip dependency installation check.",
    )
    parser.add_argument(
        "--desktop-launch",
        action="store_true",
        help="Desktop mode for packaged installation startup.",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Cross-platform entry point — setup, then dispatch to requested action."""
    args = _build_parser().parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Banner
    print(_BANNER)
    detected_os = _detect_os()
    print(f"  OS detected : {platform.system()} ({detected_os})")
    print(f"  Repository  : {_REPO_ROOT}")
    print(f"  Action      : {args.action}")
    if args.action == "serve":
        print(f"  Host:Port   : {args.host}:{args.port}")

    # ── Setup phase ────────────────────────────────────────────────────────
    _section("Step 1 — Python version")
    _check_python()

    _section("Step 2 — Environment (.env)")
    _load_dotenv()
    _ensure_data_dir()

    if not args.skip_install:
        _section("Step 3 — Dependencies")
        _ensure_deps()

    cfg_hash = _config_hash()
    _ok(f"Config hash: {cfg_hash}")

    # ── Action dispatch ────────────────────────────────────────────────────
    if args.desktop_launch:
        _run_desktop()
    elif args.action == "clean":
        _clean()
    elif args.action == "test":
        _run_tests()
    elif args.action == "validate":
        _run_validate()
    elif args.action == "check":
        _run_check()
    elif args.action == "serve":
        _run_serve(args.host, args.port, args.log_level)
    elif args.action == "none":
        _section("Setup complete")
        print("  To start:   python launch.py")
        print("  Windows:    .\\setup.ps1")
        print("  Unix:       bash setup.sh")

    print("\n  Done.\n")


if __name__ == "__main__":
    main()
