"""Command-line entry for Babel subsystem."""

from __future__ import annotations

from pathlib import Path

from thalos_prime.babel.control.semantic_orchestrator import SemanticOrchestrator

from .semantic_cli import SemanticCLI


def run_cli(storage_path: Path | None = None) -> None:
    base = storage_path or Path("./storage")
    orchestrator = SemanticOrchestrator(base)
    orchestrator.initialize()
    cli = SemanticCLI(orchestrator)
    cli.run()


if __name__ == "__main__":  # pragma: no cover
    run_cli()
