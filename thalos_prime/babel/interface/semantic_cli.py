"""Interactive CLI for Babel subsystem."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..control.semantic_orchestrator import SemanticOrchestrator

from .formatter import OutputFormatter

_SESSION_NAMESPACE = uuid.UUID("c2cdd8a5-0a70-4e12-b12b-309c2b8985ff")


class SemanticCLI:
    """Deterministic interactive CLI."""

    def __init__(self, orchestrator: SemanticOrchestrator) -> None:
        self.orchestrator = orchestrator
        self.session_id = self._derive_session_id()
        self.verbose = False

    def run(self) -> None:
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
            print(OutputFormatter.format_response(response, verbose=self.verbose))
            print()
        self._emit_event("session.terminated", "CLI loop exited deterministically")

    def _handle_command(self, command: str) -> bool:
        if command in {"/quit", "/exit"}:
            self._emit_event("session.terminate", "user requested exit")
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
            self._emit_event("checkpoint.created", f"path={path}")
            print(f"Checkpoint created at {path}")
            return True
        if command == "/reconcile":
            self.orchestrator.reconcile()
            self._emit_event("reconcile.complete", "state reconciled")
            print("Reconciliation complete")
            return True
        if command == "/verbose":
            self.verbose = not self.verbose
            self._emit_event("verbose.toggled", f"verbose={self.verbose}")
            print(f"Verbose: {self.verbose}")
            return True
        if command == "/help":
            print("Commands: /status, /checkpoint, /reconcile, /verbose, /quit")
            return True
        self._emit_event("command.unknown", command)
        print("Unknown command")
        return True

    def _derive_session_id(self) -> str:
        base_material = f"{self.orchestrator.seed}:{self.orchestrator.state.conversations_handled}"
        deterministic_uuid = uuid.uuid5(_SESSION_NAMESPACE, base_material)
        return str(deterministic_uuid)

    def _print_banner(self) -> None:
        print("=" * 60)
        print("Babel Deterministic CLI")
        print("=" * 60)
        print(f"Seed: {self.orchestrator.seed}")
        print(f"Session: {self.session_id}")
        print("Commands: /status, /checkpoint, /reconcile, /verbose, /quit")
        print()

    def _emit_event(self, event: str, detail: str) -> None:
        print(f"[event] {event} session={self.session_id} detail={detail}")
