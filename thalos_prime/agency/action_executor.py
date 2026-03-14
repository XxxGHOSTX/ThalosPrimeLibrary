"""Thalos Prime - Action Executor.

Data Plane component that executes registered actions (tool / API calls)
deterministically. Each action handler is a pure callable that receives
typed parameters and returns an ActionResult. All invocations are logged
for replay.

Data Plane boundary: executes computational work only — no lifecycle
coordination logic belongs here.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from thalos_prime.library_of_sense.core.interfaces import ValidationResult
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)

ActionHandler = Callable[[dict[str, object]], "ActionResult"]


@dataclass
class ActionExecutionError(Exception):
    """Raised by execute() when a registered handler raises an exception.

    Attributes:
        action: Name of the action that failed.
        result: The failure ActionResult produced from the handler exception.
        cause: The original exception raised by the handler.

    """

    action: str
    result: ActionResult
    cause: BaseException

    def __str__(self) -> str:
        """Return string representation."""
        return f"ActionExecutionError(action={self.action!r}, cause={self.cause!r})"


@dataclass
class ActionResult:
    """Result produced by executing an action.

    Attributes:
        action: Name of the action that was executed.
        success: Whether the action succeeded.
        output: Output data from the action.
        error: Error message if the action failed.
        executed_at: ISO-8601 timestamp of execution.

    """

    action: str
    success: bool
    output: dict[str, object] = field(default_factory=dict)
    error: str = ""
    executed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this ActionResult.

        """
        return {
            "action": self.action,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "executed_at": self.executed_at,
        }


class ActionExecutor(BaseLifecycleComponent):
    """Deterministic action executor with handler registry.

    Actions are registered by name with a handler callable. Execution is
    logged, and identical (action, params) inputs always produce identical
    results when the handlers themselves are deterministic.
    """

    def __init__(self, seed: int = 0) -> None:
        """Initialize the action executor.

        Args:
            seed: Deterministic seed for replay identification.

        """
        super().__init__("ActionExecutor", seed=seed)
        self._handlers: dict[str, ActionHandler] = {}
        self._execution_count: int = 0
        self._history: list[ActionResult] = []

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the action executor and reset state."""
        self._handlers = {}
        self._execution_count = 0
        self._history = []
        self._initialized = True
        self._emit_event("initialize", "handlers cleared, initialized=True")
        logger.debug("ActionExecutor initialized")

    def validate(self) -> ValidationResult:
        """Validate that the action executor is ready.

        Returns:
            ValidationResult indicating readiness.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="ActionExecutor not initialized; call initialize() first",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"ActionExecutor ready: handlers={len(self._handlers)} "
                f"executions={self._execution_count}"
            ),
        )

    def operate(self) -> None:
        """Log current statistics. Idempotent."""
        self._emit_event(
            "operate",
            f"handlers={len(self._handlers)} executions={self._execution_count}",
        )

    def reconcile(self) -> None:
        """Reconcile counters to non-negative values."""
        self._execution_count = max(self._execution_count, 0)
        self._emit_event(
            "reconcile",
            f"handlers={len(self._handlers)} executions={self._execution_count}",
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialize action executor state.

        Returns:
            Dict with component name, seed, handler list, and execution count.

        """
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "registered_actions": sorted(self._handlers.keys()),
            "execution_count": self._execution_count,
            "history_hash": self._history_hash(),
        }
        self._emit_event("checkpoint", f"executions={self._execution_count}")
        return state

    def terminate(self) -> None:
        """Reset action executor state."""
        self._handlers = {}
        self._execution_count = 0
        self._history = []
        self._initialized = False
        self._emit_event("terminate", "handlers cleared, initialized=False")
        logger.debug("ActionExecutor terminated")

    # ------------------------------------------------------------------
    # Data Plane methods
    # ------------------------------------------------------------------

    def register_action(self, name: str, handler: ActionHandler) -> None:
        """Register an action handler.

        Args:
            name: Unique action name.
            handler: Callable that takes a params dict and returns ActionResult.

        Raises:
            ValueError: If an action with this name is already registered.

        """
        if name in self._handlers:
            msg = f"Action '{name}' is already registered"
            raise ValueError(msg)
        self._handlers[name] = handler
        logger.debug("ActionExecutor.register_action: name=%r", name)

    def unregister_action(self, name: str) -> bool:
        """Remove a registered action handler.

        Args:
            name: The action name to unregister.

        Returns:
            True if the action existed and was removed, False otherwise.

        """
        if name in self._handlers:
            del self._handlers[name]
            return True
        return False

    def execute(self, action: str, params: dict[str, object]) -> ActionResult:
        """Execute a registered action; raise ActionExecutionError if handler throws.

        Args:
            action: Name of the registered action to execute.
            params: Parameters to pass to the action handler.

        Returns:
            ActionResult from the handler, or a failure result if the
            action is not registered.

        Raises:
            ActionExecutionError: When the registered handler raises any exception.

        """
        handler = self._handlers.get(action)
        if handler is None:
            result = ActionResult(
                action=action,
                success=False,
                error=f"Unknown action: {action}",
            )
            self._history.append(result)
            self._execution_count += 1
            logger.warning("ActionExecutor.execute: unknown action %r", action)
            return result

        try:
            result = handler(params)
        except Exception as exc:
            failure = ActionResult(
                action=action,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )
            logger.exception("ActionExecutor.execute: handler raised for %r", action)
            raise ActionExecutionError(action=action, result=failure, cause=exc) from exc

        self._history.append(result)
        self._execution_count += 1
        logger.debug(
            "ActionExecutor.execute: action=%r success=%s",
            action,
            result.success,
        )
        return result

    def safe_execute(self, action: str, params: dict[str, object]) -> ActionResult:
        """Execute a registered action; capture any handler exception as a failure result.

        Args:
            action: Name of the registered action to execute.
            params: Parameters to pass to the action handler.

        Returns:
            ActionResult from the handler, or a failure ActionResult if the
            action is not registered or the handler raises.

        """
        try:
            return self.execute(action, params)
        except ActionExecutionError as err:
            result = err.result
            self._history.append(result)
            self._execution_count += 1
            logger.debug(
                "ActionExecutor.safe_execute: captured error for %r: %s",
                action,
                err,
            )
            return result

    def get_history(self) -> list[ActionResult]:
        """Return an immutable copy of the execution history.

        Returns:
            List of ActionResult in chronological order.

        """
        return list(self._history)

    @property
    def registered_actions(self) -> list[str]:
        """Return sorted list of registered action names."""
        return sorted(self._handlers.keys())

    def _history_hash(self) -> str:
        """Compute a deterministic hash of execution history.

        Returns:
            Hex digest string of the SHA-256 hash over history entries.

        """
        hasher = hashlib.sha256()
        for result in self._history:
            hasher.update(f"{result.action}:{result.success}:{result.error}".encode())
        return hasher.hexdigest()


__all__ = ["ActionExecutionError", "ActionExecutor", "ActionHandler", "ActionResult"]
