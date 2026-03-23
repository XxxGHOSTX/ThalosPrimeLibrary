#!/usr/bin/env python3
"""Thalos Prime Runtime Entrypoint.

Loads plugins, initializes the RuntimeEngine, executes the built-in
'legacy' task to verify end-to-end operation, and optionally starts
the Thalos Prime API server.

Usage::

    python run_thalos.py                 # initialize and run legacy task
    python run_thalos.py --serve         # also start API server
    python run_thalos.py --serve --port 9000

All existing thalos_prime code is accessed exclusively through the
LegacyPlugin / LegacyAdapter in thalos_runtime.plugins.legacy_adapter.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Ensure the workspace root is on the path when run directly.
_workspace_root = os.path.dirname(os.path.abspath(__file__))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

_HOST: str = "127.0.0.1"
_PORT: int = 8000


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for run_thalos.py.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="run_thalos",
        description="Thalos Prime Runtime entrypoint",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the Thalos Prime API server after initialization.",
    )
    parser.add_argument(
        "--host",
        default=_HOST,
        help=f"Server bind host (default: {_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_PORT,
        help=f"Server bind port (default: {_PORT}).",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity level (default: WARNING).",
    )
    return parser


def main() -> None:
    """Initialize the runtime, execute the 'legacy' task, and optionally serve."""
    args = _build_parser().parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level))

    print("=" * 60)
    print("Thalos Prime Runtime v1.0")
    print("=" * 60)

    from thalos_runtime.core.engine import RuntimeEngine
    from thalos_runtime.core.deps import set_engine
    from thalos_runtime.plugins.loader import PluginLoader

    print("\nLoading plugins...")
    engine = RuntimeEngine()
    loader = PluginLoader()
    registered = loader.discover_and_register(engine)
    print(f"  Plugins registered: {registered}")

    print("\nInitializing engine...")
    engine.initialize()
    validation = engine.validate()
    print(f"  Validation: {validation.message}")
    set_engine(engine)

    print("\nRunning 'legacy' task...")
    result = engine.execute("legacy", {"query": "thalos prime runtime test"})
    print(f"\nResult:\n{result}")

    print("\n" + "-" * 60)
    print("Runtime initialized and 'legacy' task executed successfully.")

    if args.serve:
        print(f"\nStarting API server on {args.host}:{args.port} ...")
        try:
            import uvicorn

            from thalos_prime.api.server import app as thalos_app

            uvicorn.run(
                thalos_app,
                host=args.host,
                port=args.port,
                log_level="info",
            )
        except KeyboardInterrupt:
            print("\nShutdown requested by user.")


if __name__ == "__main__":
    main()
