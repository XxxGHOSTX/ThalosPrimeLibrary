"""Interactive CLI for Babel subsystem."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from thalos_prime.babel.control.semantic_orchestrator import SemanticOrchestrator

_SESSION_NAMESPACE = uuid.UUID("c2cdd8a5-0a70-4e12-b12b-309c2b8985ff")


class SemanticCLI:
    """Deterministic interactive CLI."""

    def __init__(self, orchestrator: SemanticOrchestrator) -> None:
        """Initialize the semantic CLI."""
        self.orchestrator = orchestrator
        self.session_id = self._derive_session_id()
        self.verbose = False

    def run(self) -> None:
        """Run the interactive CLI loop."""
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
        def _quit() -> bool:
            self._emit_event("session.terminate", "user requested exit")
            return False

        def _status() -> bool:
            self.orchestrator.get_status()
            return True

        def _checkpoint() -> bool:
            path = self.orchestrator.checkpoint()
            self._emit_event("checkpoint.created", f"path={path}")
            return True

        def _reconcile() -> bool:
            self.orchestrator.reconcile()
            self._emit_event("reconcile.complete", "state reconciled")
            return True

        def _verbose() -> bool:
            self.verbose = not self.verbose
            self._emit_event("verbose.toggled", f"verbose={self.verbose}")
            return True

        def _help() -> bool:
            return True

        dispatch: dict[str, Callable[[], bool]] = {
            "/quit": _quit,
            "/exit": _quit,
            "/status": _status,
            "/checkpoint": _checkpoint,
            "/reconcile": _reconcile,
            "/verbose": _verbose,
            "/help": _help,
        }
        handler = dispatch.get(command)
        if handler is None:
            self._emit_event("command.unknown", command)
            return True
        return handler()

    def _derive_session_id(self) -> str:
        base_material = f"{self.orchestrator.seed}:{self.orchestrator.state.conversations_handled}"
        deterministic_uuid = uuid.uuid5(_SESSION_NAMESPACE, base_material)
        return str(deterministic_uuid)

    def _print_banner(self) -> None:
        pass

    def _emit_event(self, event: str, detail: str) -> None:
        pass
