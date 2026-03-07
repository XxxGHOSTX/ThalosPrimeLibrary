"""Interactive CLI for Babel subsystem."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from thalos_prime.babel.control.semantic_orchestrator import SemanticOrchestrator

_SESSION_NAMESPACE = uuid.UUID("c2cdd8a5-0a70-4e12-b12b-309c2b8985ff")


class SemanticCLI:
    """Deterministic interactive CLI."""

    def __init__(self, orchestrator: SemanticOrchestrator) -> None:
        """Initialize the CLI with an orchestrator and derive a deterministic session ID."""
        self.orchestrator = orchestrator
        self.session_id = self._derive_session_id()
        self.verbose = False

    def run(self) -> None:
        """Run the interactive CLI loop until the user exits or EOF is received."""
        self._print_banner()
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                self._emit_event("session.complete", "EOF received; deterministic shutdown")
                break
            except KeyboardInterrupt:
                self._emit_event("session.interrupted", "KeyboardInterrupt received; terminating")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                if not self._handle_command(user_input):
                    break
                continue

            try:
                response = self.orchestrator.handle_semantic_input(user_input, self.session_id)
            except Exception as exc:
                self._emit_event("response.error", str(exc))
                raise

            self._emit_event("response.generated", f"coordinate={response.coordinate}")
        self._emit_event("session.terminated", "CLI loop exited deterministically")

    def _handle_command(self, command: str) -> bool:
        if command in {"/quit", "/exit"}:
            self._emit_event("session.terminate", "user requested exit")
            return False
        if command == "/status":
            self.orchestrator.get_status()
            return True
        if command == "/checkpoint":
            path = self.orchestrator.checkpoint()
            self._emit_event("checkpoint.created", f"path={path}")
            return True
        if command == "/reconcile":
            self.orchestrator.reconcile()
            self._emit_event("reconcile.complete", "state reconciled")
            return True
        if command == "/verbose":
            self.verbose = not self.verbose
            self._emit_event("verbose.toggled", f"verbose={self.verbose}")
            return True
        if command == "/help":
            return True
        self._emit_event("command.unknown", command)
        return True

    def _derive_session_id(self) -> str:
        base_material = f"{self.orchestrator.seed}:{self.orchestrator.state.conversations_handled}"
        deterministic_uuid = uuid.uuid5(_SESSION_NAMESPACE, base_material)
        return str(deterministic_uuid)

    def _print_banner(self) -> None:
        pass

    def _emit_event(self, event: str, detail: str) -> None:
        pass
