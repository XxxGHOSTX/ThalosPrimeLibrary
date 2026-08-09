#!/usr/bin/env python3
"""Thalos Prime — Matrix-themed launch UI.

Starts all background services and the API server with a full-screen
Rich terminal dashboard featuring:

- ASCII Matrix rain animation in the left panel.
- Real-time system status and worker health in the centre panel.
- Live metrics (CPU, memory, coherence scores) in the right panel.
- Scrolling log stream at the bottom.

Usage::

    python launch_ui.py [--host HOST] [--port PORT] [--no-server]

Press ``q`` or ``Ctrl-C`` to stop.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import random
import subprocess
import sys
import threading
import time
from typing import Any

# ---------------------------------------------------------------------------
# Optional rich import — degrade gracefully if unavailable
# ---------------------------------------------------------------------------
try:
    from rich import box
    from rich.columns import Columns
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.style import Style
    from rich.table import Table
    from rich.text import Text

    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MATRIX_CHARS = (
    "ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ"
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "αβγδεζηθικλμνξοπρστυφχψω"
)
_RAIN_WIDTH = 28
_RAIN_HEIGHT = 22
_REFRESH_RATE = 4  # frames per second
_LOG_BUFFER_SIZE = 40

_BANNER = r"""
  _____ _           _            ____       _
 |_   _| |__   __ _| | ___  ___  |  _ \ _ __(_)_ __ ___   ___
   | | | '_ \ / _` | |/ _ \/ __| | |_) | '__| | '_ ` _ \ / _ \
   | | | | | | (_| | | (_) \__ \ |  __/| |  | | | | | | |  __/
   |_| |_| |_|\__,_|_|\___/|___/ |_|   |_|  |_|_| |_| |_|\___|
""".strip(
    "\n"
)

_STATUS_LABELS: dict[str, str] = {
    "API Server": "◉",
    "Orchestrator": "◉",
    "Coherence Amplification": "◉",
    "Knowledge Graph": "◉",
    "Constraint Solver": "◉",
    "Cache Warmer": "◉",
    "Session Manager": "◉",
    "Evidence Gathering": "◉",
    "Performance Monitor": "◉",
}

# ---------------------------------------------------------------------------
# Logging bridge — captures log records into a ring buffer for the UI
# ---------------------------------------------------------------------------

_log_buffer: list[str] = []
_log_lock = threading.Lock()


class _UILogHandler(logging.Handler):
    """Captures log records into the shared ring buffer."""

    def emit(self, record: logging.LogRecord) -> None:
        line = self.format(record)
        with _log_lock:
            _log_buffer.append(line)
            if len(_log_buffer) > _LOG_BUFFER_SIZE:
                _log_buffer.pop(0)


_ui_handler = _UILogHandler()
_ui_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
logging.getLogger().addHandler(_ui_handler)
logging.getLogger().setLevel(logging.INFO)


def _get_logs() -> list[str]:
    with _log_lock:
        return list(_log_buffer)


# ---------------------------------------------------------------------------
# Matrix rain state
# ---------------------------------------------------------------------------


class MatrixRain:
    """Maintains per-column state for the Matrix rain animation."""

    def __init__(self, width: int = _RAIN_WIDTH, height: int = _RAIN_HEIGHT) -> None:
        self._width = width
        self._height = height
        self._rng = random.Random(42)
        # Each column: (current_head_row, speed, chars_list)
        self._columns: list[dict[str, Any]] = [
            {
                "head": self._rng.randint(0, height),
                "speed": self._rng.uniform(0.3, 1.0),
                "last_tick": 0.0,
                "trail": [""] * height,
            }
            for _ in range(width)
        ]

    def tick(self) -> None:
        """Advance one animation frame for all columns."""
        now = time.monotonic()
        for col in self._columns:
            if now - col["last_tick"] < col["speed"]:
                continue
            col["last_tick"] = now
            head: int = int(col["head"])
            trail: list[str] = col["trail"]
            # Move head down, wrap at height
            col["head"] = (head + 1) % (self._height + 4)
            new_head = int(col["head"])
            # Draw new character at head position
            if new_head < self._height:
                trail[new_head] = self._rng.choice(_MATRIX_CHARS)
            # Fade trailing characters (blank them after a while)
            fade_row = (new_head - 8) % self._height
            trail[fade_row] = ""

    def render_rich(self) -> "Text":
        """Render the rain as a Rich Text object.

        Returns:
            Rich Text with green Matrix rain characters.

        """
        if not _RICH_AVAILABLE:  # pragma: no cover
            return Text("")  # type: ignore[no-untyped-call]

        text = Text()
        for row in range(self._height):
            for col_idx, col in enumerate(self._columns):
                trail: list[str] = col["trail"]
                ch = trail[row] if row < len(trail) else ""
                head_row = int(col["head"]) % self._height
                if not ch:
                    text.append(" ")
                elif row == head_row:
                    text.append(ch, style=Style(color="bright_white", bold=True))
                else:
                    text.append(ch, style=Style(color="green"))
            if col_idx < self._width - 1 or True:
                text.append("\n")
        return text


# ---------------------------------------------------------------------------
# Dashboard layout builders
# ---------------------------------------------------------------------------


def _build_banner_panel() -> "Panel":
    """Build the ASCII art banner panel."""
    banner_text = Text(_BANNER, style=Style(color="bright_green", bold=True))
    return Panel(
        banner_text,
        title="[bright_green bold]THALOS PRIME[/]",
        border_style="green",
    )


def _build_rain_panel(rain: "MatrixRain") -> "Panel":
    """Build the Matrix rain panel."""
    rain.tick()
    return Panel(
        rain.render_rich(),
        title="[green]DATA STREAM[/]",
        border_style="green",
    )


def _build_status_panel(orchestrator_metrics: dict[str, Any] | None) -> "Panel":
    """Build the system status panel.

    Args:
        orchestrator_metrics: Live metrics from the autonomous orchestrator.

    Returns:
        Rich Panel with worker status table.

    """
    table = Table(
        show_header=True,
        header_style="bold green",
        box=box.SIMPLE,  # type: ignore[attr-defined]
        border_style="green",
    )
    table.add_column("Subsystem", style="green")
    table.add_column("Status", justify="center")
    table.add_column("Step", justify="right", style="dim green")

    worker_data: dict[str, Any] = {}
    if orchestrator_metrics:
        worker_data = orchestrator_metrics.get("workers", {})

    status_map: dict[str, tuple[str, str, str]] = {
        "coherence_amplification": ("Coherence Amplification", "◉", "bright_green"),
        "knowledge_graph_enrichment": ("Knowledge Graph", "◉", "bright_green"),
        "constraint_solving": ("Constraint Solver", "◉", "bright_green"),
        "cache_warming": ("Cache Warmer", "◉", "bright_green"),
        "session_maintenance": ("Session Manager", "◉", "bright_green"),
        "evidence_gathering": ("Evidence Gathering", "◉", "bright_green"),
        "performance_metrics": ("Performance Monitor", "◉", "bright_green"),
    }
    for wk, (label, icon, colour) in status_map.items():
        step = 0
        if wk in worker_data:
            step = int(worker_data[wk].get("step", 0))
        table.add_row(label, Text(icon, style=colour), str(step))

    uptime = 0.0
    if orchestrator_metrics:
        uptime = float(orchestrator_metrics.get("uptime_s", 0.0))
    uptime_str = f"Uptime: {uptime:.0f}s"
    return Panel(
        table,
        title=f"[bright_green bold]SYSTEM STATUS  {uptime_str}[/]",
        border_style="bright_green",
    )


def _build_metrics_panel(orchestrator_metrics: dict[str, Any] | None) -> "Panel":
    """Build the real-time metrics panel.

    Args:
        orchestrator_metrics: Live metrics from the autonomous orchestrator.

    Returns:
        Rich Panel with CPU, memory, and worker stats.

    """
    table = Table(
        show_header=False,
        box=box.SIMPLE,  # type: ignore[attr-defined]
        border_style="green",
        expand=True,
    )
    table.add_column("Metric", style="green")
    table.add_column("Value", style="bright_green", justify="right")

    system: dict[str, Any] = {}
    if orchestrator_metrics:
        system = orchestrator_metrics.get("system", {})

    cpu_pct = float(system.get("cpu_percent", 0.0))
    mem_mib = float(system.get("mem_rss_mib", 0.0))

    total_steps = 0
    total_errors = 0
    if orchestrator_metrics:
        for wk in orchestrator_metrics.get("workers", {}).values():
            total_steps += int(wk.get("step", 0))
            total_errors += int(wk.get("error_count", 0))

    table.add_row("CPU Usage", f"{cpu_pct:.1f}%")
    table.add_row("Memory (RSS)", f"{mem_mib:.1f} MiB")
    table.add_row("Worker Cycles", str(total_steps))
    table.add_row("Worker Errors", str(total_errors))
    table.add_row("Python PID", str(os.getpid()))
    table.add_row("Workers Active", str(orchestrator_metrics.get("worker_count", 0) if orchestrator_metrics else 0))

    return Panel(
        table,
        title="[bright_green bold]LIVE METRICS[/]",
        border_style="bright_green",
    )


def _build_log_panel() -> "Panel":
    """Build the scrolling log panel from the ring buffer."""
    logs = _get_logs()
    text = Text()
    for line in logs[-12:]:
        # Colour-code by level
        if "ERROR" in line or "CRITICAL" in line:
            text.append(line + "\n", style="red")
        elif "WARNING" in line:
            text.append(line + "\n", style="yellow")
        elif "INFO" in line:
            text.append(line + "\n", style="green")
        else:
            text.append(line + "\n", style="dim green")
    return Panel(
        text,
        title="[green]LIVE LOG STREAM[/]",
        border_style="green",
    )


def _build_layout(
    rain: "MatrixRain",
    orchestrator_metrics: dict[str, Any] | None,
) -> "Layout":
    """Compose the full-screen layout for one render frame.

    Args:
        rain: MatrixRain animation state object.
        orchestrator_metrics: Live metrics dict from orchestrator.

    Returns:
        Composed Rich Layout ready for rendering.

    """
    layout = Layout()
    layout.split_column(
        Layout(name="banner", size=7),
        Layout(name="body"),
        Layout(name="logs", size=16),
    )
    layout["body"].split_row(
        Layout(name="rain", ratio=2),
        Layout(name="status", ratio=3),
        Layout(name="metrics", ratio=2),
    )
    layout["banner"].update(_build_banner_panel())
    layout["rain"].update(_build_rain_panel(rain))
    layout["status"].update(_build_status_panel(orchestrator_metrics))
    layout["metrics"].update(_build_metrics_panel(orchestrator_metrics))
    layout["logs"].update(_build_log_panel())
    return layout


# ---------------------------------------------------------------------------
# Fallback plain-text mode (when rich is not installed)
# ---------------------------------------------------------------------------


def _run_plain_mode(host: str, port: int) -> None:
    """Run in plain-text mode without Rich."""
    print("=" * 62)
    print("  THALOS PRIME — Sovereign Epistemic Operating System")
    print("=" * 62)
    print("  [INFO] Rich library not found — running in plain mode.")
    print(f"  [INFO] API server: http://{host}:{port}")
    print("  [INFO] Starting autonomous orchestrator...")

    from thalos_prime.autonomous.orchestrator import start_orchestrator

    orch = start_orchestrator(seed=0)
    logging.getLogger(__name__).info("Autonomous orchestrator started: %s", orch.validate().message)

    print("  [INFO] Starting API server (Ctrl-C to stop)...")
    _start_server(host, port)


# ---------------------------------------------------------------------------
# Server subprocess launcher
# ---------------------------------------------------------------------------

_server_proc: subprocess.Popen[bytes] | None = None


def _start_server(host: str, port: int) -> None:
    """Start the API server in the current process (blocking)."""
    import uvicorn

    from thalos_prime.api.server import app as thalos_app

    uvicorn.run(thalos_app, host=host, port=port, log_level="info")


def _start_server_background(host: str, port: int) -> threading.Thread:
    """Start the API server in a background daemon thread.

    Args:
        host: Bind host for uvicorn.
        port: Bind port for uvicorn.

    Returns:
        The started daemon thread.

    """
    thread = threading.Thread(
        target=_start_server,
        args=(host, port),
        name="thalos-api-server",
        daemon=True,
    )
    thread.start()
    return thread


# ---------------------------------------------------------------------------
# Main Rich UI loop
# ---------------------------------------------------------------------------


def _run_rich_ui(host: str, port: int, no_server: bool) -> None:
    """Run the full Matrix-themed Rich terminal UI.

    Args:
        host: API server bind host.
        port: API server bind port.
        no_server: If True, skip starting the API server.

    """
    console = Console()

    # Start orchestrator
    from thalos_prime.autonomous.orchestrator import start_orchestrator

    orch_seed_input = f"launch_ui:{os.getpid()}".encode()
    orch_seed = int(hashlib.sha256(orch_seed_input).hexdigest()[:8], 16)
    orch = start_orchestrator(seed=orch_seed)
    logging.getLogger(__name__).info("Autonomous orchestrator started")

    # Optionally start server in background
    if not no_server:
        logging.getLogger(__name__).info(
            "Starting API server on http://%s:%d", host, port
        )
        _start_server_background(host, port)

    rain = MatrixRain(width=_RAIN_WIDTH, height=_RAIN_HEIGHT)

    console.print(
        "[bright_green bold]INITIALIZING THALOS PRIME...[/]",
        justify="center",
    )
    time.sleep(0.3)

    try:
        with Live(
            _build_layout(rain, orch.get_metrics()),
            console=console,
            refresh_per_second=_REFRESH_RATE,
            screen=True,
        ) as live:
            while True:
                metrics = orch.get_metrics()
                live.update(_build_layout(rain, metrics))
                time.sleep(1.0 / _REFRESH_RATE)
    except KeyboardInterrupt:
        pass
    finally:
        orch.terminate()
        console.print("[bright_green bold]THALOS PRIME — SHUTDOWN COMPLETE[/]", justify="center")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python launch_ui.py",
        description="Thalos Prime Matrix UI Launcher",
    )
    parser.add_argument("--host", default="127.0.0.1", help="API server bind host.")
    parser.add_argument("--port", type=int, default=8000, help="API server bind port.")
    parser.add_argument(
        "--no-server",
        action="store_true",
        help="Start UI without launching the API server.",
    )
    return parser


def main() -> None:
    """Entry point for the Matrix-themed Thalos Prime launcher."""
    args = _build_parser().parse_args()

    if not _RICH_AVAILABLE:
        _run_plain_mode(args.host, args.port)
        return

    _run_rich_ui(args.host, args.port, args.no_server)


if __name__ == "__main__":
    main()
