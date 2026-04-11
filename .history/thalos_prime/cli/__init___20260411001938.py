"""Thalos Prime CLI subsystem.

Exports the ``run_cli`` entry point and ``build_parser`` for programmatic
access to the command-line interface.
"""

from thalos_prime.cli.commands import build_parser, run_cli

__all__ = ["build_parser", "run_cli"]
