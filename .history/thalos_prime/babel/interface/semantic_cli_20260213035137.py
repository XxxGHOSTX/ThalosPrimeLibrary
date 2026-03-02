"""
Interactive CLI for Babel subsystem.
"""

from __future__ import annotations

import uuid
from typing import Optional

from ..control.semantic_orchestrator import SemanticOrchestrator
from .formatter import OutputFormatter


class SemanticCLI:
    """Deterministic interactive CLI."""

    def __init__(self, orchestrator: SemanticOrchestrator):
        self.orchestrator = orchestrator
        self.session_id = str(uuid.uuid4())
        self.verbose = False

    def run(self) -> None:
        print("=" * 60)
        print("Babel Deterministic CLI")
        print("=" * 60)
        print(f"Session: {self.session_id}")
        print("Commands: /status, /checkpoint, /reconcile, /verbose, /quit")
        print()
        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.startswith("/"):
                    if not self._handle_command(user_input):
                        break
                    continue
                response = self.orchestrator.handle_semantic_input(user_input, self.session_id)
                print(OutputFormatter.format_response(response, verbose=self.verbose))
                print()
            except KeyboardInterrupt:
                print("\nInterrupted; use /quit to exit deterministically.")
            except Exception as exc:  # noqa: BLE001
                print(f"Error: {exc}")

    def _handle_command(self, command: str) -> bool:
        if command in {"/quit", "/exit"}:
            return False
        if command == "/status":
            status = self.orchestrator.get_status()
            print(f"Phase: {status.phase.name}")
            print(f"Conversations: {status.conversations_handled}")
            print(f"Last coordinate: {status.last_coordinate}")
            print(f"Integrity: {status.integrity_verified}")
            return True
        if command == "/checkpoint":
            path = self.orchestrator.checkpoint()
            print(f"Checkpoint created at {path}")
            return True
        if command == "/reconcile":
            self.orchestrator.reconcile()
            print("Reconciliation complete")
            return True
        if command == "/verbose":
            self.verbose = not self.verbose
            print(f"Verbose: {self.verbose}")
            return True
        print("Unknown command")
        return True
