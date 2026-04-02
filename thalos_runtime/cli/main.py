"""Minimal CLI for thalos_runtime.

Supports ``--task`` and ``--data`` flags to execute tasks via the
RuntimeEngine.  Initializes the engine, loads all plugins, executes
the requested task, and prints the JSON-encoded result to stdout.

Control Plane: parses arguments and coordinates engine initialization.
Data Plane: computation is dispatched through engine.execute().

Usage::

    python -m thalos_runtime.cli.main --task legacy
    python -m thalos_runtime.cli.main --task legacy --data '{"query": "hello"}'
    python -m thalos_runtime.cli.main --task legacy --log-level DEBUG
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from thalos_runtime.core.engine import RuntimeEngine
from thalos_runtime.plugins.loader import PluginLoader

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the thalos_runtime CLI.

    Returns:
        Configured ArgumentParser with --task, --data, and --log-level.

    """
    parser = argparse.ArgumentParser(
        prog="thalos_runtime",
        description="Thalos Runtime CLI - execute registered tasks",
    )
    parser.add_argument(
        "--task",
        required=True,
        help="Task name to execute (e.g. 'legacy').",
    )
    parser.add_argument(
        "--data",
        default="{}",
        help="JSON-encoded payload dict for the task (default: '{}').",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity level (default: WARNING).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: initialize engine, execute task, print result.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on any error.

    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        payload: dict[str, Any] = json.loads(args.data)
    except json.JSONDecodeError as exc:
        print(  # noqa: T201
            f"Error: --data is not valid JSON: {exc}",
            file=sys.stderr,
        )
        return 1

    engine = RuntimeEngine()
    loader = PluginLoader()
    loader.discover_and_register(engine)
    engine.initialize()

    from thalos_runtime.core.executor import ExecutionError
    from thalos_runtime.core.registry import RegistryError

    try:
        result = engine.execute(args.task, payload)
    except RegistryError as exc:
        print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
        return 1
    except ExecutionError as exc:
        print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
        return 1

    print(json.dumps(result, indent=2, default=str))  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
