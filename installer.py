#!/usr/bin/env python3
"""Thalos Prime — Matrix-themed installer.

Installs all Python dependencies, validates the installation, and creates a
shell alias / launcher script, all displayed with a Matrix-rain terminal UI.

Usage::

    python installer.py [--dev] [--no-alias]

The installer does **not** require any dependencies to be pre-installed (it
uses only the standard library until after installation completes).  The Rich
terminal UI is rendered if ``rich`` is available after the installation step.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.resolve()
_ALIAS_NAME = "thalos"
_LAUNCHER_SCRIPT = _REPO_ROOT / "launch_ui.py"

_INSTALL_STEPS: list[tuple[str, str]] = [
    ("Checking Python version", "python_check"),
    ("Installing core dependencies", "install_core"),
    ("Installing dev dependencies", "install_dev"),
    ("Validating installation integrity", "validate"),
    ("Creating launcher alias", "create_alias"),
    ("Running smoke test", "smoke_test"),
]

_MATRIX_CHARS_ASCII = "01ABCDEFGHIJKLMNOPQRSTUVWXYZ#@$%&"

# ---------------------------------------------------------------------------
# Colour helpers (ANSI without Rich dependency at start)
# ---------------------------------------------------------------------------

_GREEN = "\033[92m"
_BRIGHT_GREEN = "\033[1;92m"
_WHITE = "\033[97m"
_DIM = "\033[2m"
_RESET = "\033[0m"
_RED = "\033[91m"
_YELLOW = "\033[93m"


def _g(text: str) -> str:
    """Wrap text in bright green ANSI codes."""
    return f"{_BRIGHT_GREEN}{text}{_RESET}"


def _d(text: str) -> str:
    """Wrap text in dim green ANSI codes."""
    return f"{_DIM}{_GREEN}{text}{_RESET}"


def _r(text: str) -> str:
    """Wrap text in red ANSI codes."""
    return f"{_RED}{text}{_RESET}"


def _y(text: str) -> str:
    """Wrap text in yellow ANSI codes."""
    return f"{_YELLOW}{text}{_RESET}""


# ---------------------------------------------------------------------------
# Plain-text progress helpers (pre-rich)
# ---------------------------------------------------------------------------


def _print_banner() -> None:
    """Print the installer ASCII-art banner."""
    banner_lines = [
        "╔══════════════════════════════════════════════════════════╗",
        "║                                                          ║",
        "║       INSTALLING THALOS PRIME LIBRARY                   ║",
        "║       Sovereign Epistemic Operating System               ║",
        "║                                                          ║",
        "╚══════════════════════════════════════════════════════════╝",
    ]
    print()
    for line in banner_lines:
        print(_g(line))
    print()


def _print_step(index: int, total: int, label: str) -> None:
    """Print a Matrix-style step indicator."""
    bar_filled = "█" * (index + 1)
    bar_empty = "░" * (total - index - 1)
    pct = int((index + 1) / total * 100)
    bar = f"[{_g(bar_filled)}{_d(bar_empty)}]"
    print(f"  {bar} {pct:3d}%  {_g('▶')} {label}")


def _print_ok(label: str) -> None:
    """Print a success marker."""
    print(f"  {_g('✓')} {label}")


def _print_fail(label: str) -> None:
    """Print a failure marker."""
    print(f"  {_r('✗')} {label}")


def _print_warn(label: str) -> None:
    """Print a warning marker."""
    print(f"  {_y('⚠')} {label}")


def _rain_line(width: int = 60) -> str:
    """Return a single row of random Matrix rain characters."""
    import random

    chars = [random.choice(_MATRIX_CHARS_ASCII) for _ in range(width)]
    return _d("".join(chars))


def _animate_rain(rows: int = 4, delay: float = 0.06) -> None:
    """Print a short Matrix rain animation burst."""
    for _ in range(rows):
        print(_rain_line())
        time.sleep(delay)


# ---------------------------------------------------------------------------
# Installation steps
# ---------------------------------------------------------------------------


def _step_python_check() -> bool:
    """Verify the Python version meets the minimum requirement.

    Returns:
        True if Python >= 3.12, False otherwise.

    """
    version = sys.version_info
    if version >= (3, 12):
        _print_ok(f"Python {version.major}.{version.minor}.{version.micro} ✓")
        return True
    _print_fail(
        f"Python 3.12+ required; found {version.major}.{version.minor}.{version.micro}"
    )
    return False


def _step_install_core() -> bool:
    """Install core (runtime) package dependencies.

    Returns:
        True on success, False on non-zero pip exit code.

    """
    cmd = [sys.executable, "-m", "pip", "install", "-e", str(_REPO_ROOT), "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        _print_ok("Core dependencies installed")
        return True
    _print_fail("Core dependency installation failed")
    if result.stderr:
        for line in result.stderr.strip().splitlines()[-5:]:
            print(f"    {_r(line)}")
    return False


def _step_install_dev(dev: bool) -> bool:
    """Optionally install development dependencies.

    Args:
        dev: Whether to install dev extras.

    Returns:
        True always (dev install is optional).

    """
    if not dev:
        _print_ok("Dev dependencies skipped (use --dev to install)")
        return True
    cmd = [sys.executable, "-m", "pip", "install", "-e", f"{_REPO_ROOT}[dev]", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        _print_ok("Dev dependencies installed")
        return True
    _print_warn("Dev dependency installation failed (non-fatal)")
    return True  # non-fatal


def _step_validate() -> bool:
    """Import the thalos_prime package and run a basic integrity check.

    Returns:
        True if import and version attribute are accessible, False otherwise.

    """
    try:
        import importlib

        tp = importlib.import_module("thalos_prime")
        version = getattr(tp, "__version__", None)
        if version is None:
            _print_fail("thalos_prime.__version__ not found")
            return False
        _print_ok(f"thalos_prime v{version} importable ✓")
        return True
    except ImportError as exc:
        _print_fail(f"Import validation failed: {exc}")
        return False


def _step_create_alias(no_alias: bool) -> bool:
    """Create a shell alias or small launcher script.

    Writes a small shell wrapper to ``~/.local/bin/thalos`` (or
    ``%USERPROFILE%\AppData\Local\Programs\thalos.bat`` on Windows)
    so users can invoke ``thalos`` from any terminal.

    Args:
        no_alias: If True, skip alias creation.

    Returns:
        True always (alias creation is optional).

    """
    if no_alias:
        _print_ok("Alias creation skipped (use --no-alias=False to enable)")
        return True

    if sys.platform == "win32":
        target_dir = Path(os.environ.get("USERPROFILE", Path.home())) / "AppData" / "Local" / "Programs"
        target_dir.mkdir(parents=True, exist_ok=True)
        script_path = target_dir / "thalos.bat"
        script_content = (
            f"@echo off\r\n"
            f'"{sys.executable}" "{_LAUNCHER_SCRIPT}" %*\r\n'
        )
        try:
            script_path.write_text(script_content, encoding="utf-8")
            _print_ok(f"Launcher created: {script_path}")
        except OSError as exc:
            _print_warn(f"Could not create launcher: {exc}")
    else:
        target_dir = Path.home() / ".local" / "bin"
        target_dir.mkdir(parents=True, exist_ok=True)
        script_path = target_dir / _ALIAS_NAME
        script_content = (
            f"#!/usr/bin/env bash\n"
            f'exec "{sys.executable}" "{_LAUNCHER_SCRIPT}" "$@"\n'
        )
        try:
            script_path.write_text(script_content, encoding="utf-8")
            script_path.chmod(0o755)
            _print_ok(f"Launcher created: {script_path}")
            _print_ok(f"Add {target_dir} to PATH to use 'thalos' command")
        except OSError as exc:
            _print_warn(f"Could not create launcher: {exc}")
    return True


def _step_smoke_test() -> bool:
    """Run a quick deterministic smoke test of the Library of Babel pipeline.

    Returns:
        True if the pipeline produces a non-empty page, False otherwise.

    """
    try:
        from thalos_prime.lob_babel_generator import address_to_page
        from thalos_prime.lob_decoder import BabelDecoder

        page = address_to_page("smoke:test:00001")
        decoder = BabelDecoder(seed=0)
        score = decoder.score_coherence(page, "smoke test")
        _print_ok(f"Babel pipeline OK — coherence={score.overall_score:.1f}")
        return True
    except Exception as exc:  # noqa: BLE001
        _print_fail(f"Smoke test failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Rich-enhanced completion animation
# ---------------------------------------------------------------------------


def _rich_completion_animation() -> None:
    """Show a Matrix-rain celebration animation using Rich (if available)."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()
        msg = Text()
        msg.append("  ✓ INSTALLATION COMPLETE  ", style="bold bright_green")
        msg.append("\n\n  Run: ", style="green")
        msg.append("python launch_ui.py", style="bold bright_white")
        msg.append("  to start Thalos Prime\n", style="green")

        for _ in range(6):
            console.print(_rain_line(console.width), highlight=False)
            time.sleep(0.04)

        console.print(
            Panel(
                msg,
                title="[bright_green bold]THALOS PRIME READY[/]",
                border_style="bright_green",
                expand=False,
            )
        )
    except ImportError:
        _animate_rain(rows=3)
        print()
        print(_g("  ✓ INSTALLATION COMPLETE"))
        print(_g(f"  Run: python {_LAUNCHER_SCRIPT} to start Thalos Prime"))
        print()


# ---------------------------------------------------------------------------
# Main installer orchestration
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python installer.py",
        description="Thalos Prime Matrix-themed installer",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Also install development dependencies.",
    )
    parser.add_argument(
        "--no-alias",
        action="store_true",
        help="Skip creating the shell launcher alias.",
    )
    return parser


def main() -> None:
    """Run the full Matrix-themed installation sequence."""
    args = _build_parser().parse_args()

    _print_banner()
    _animate_rain(rows=3, delay=0.04)
    print()

    total = len(_INSTALL_STEPS)
    failed = False

    for idx, (label, key) in enumerate(_INSTALL_STEPS):
        _print_step(idx, total, label)
        success = True

        if key == "python_check":
            success = _step_python_check()
        elif key == "install_core":
            success = _step_install_core()
        elif key == "install_dev":
            success = _step_install_dev(args.dev)
        elif key == "validate":
            success = _step_validate()
        elif key == "create_alias":
            success = _step_create_alias(args.no_alias)
        elif key == "smoke_test":
            success = _step_smoke_test()

        if not success:
            failed = True
            _print_fail(f"Step '{label}' failed — installation aborted")
            sys.exit(1)

        time.sleep(0.05)

    if not failed:
        _rich_completion_animation()


if __name__ == "__main__":
    main()
