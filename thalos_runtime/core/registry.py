"""Task registry - Control Plane lookup table for thalos_runtime.

Maps task names to TaskHandler instances.  Provides explicit, typed
registration and lookup so the engine can dispatch work without
implicit globals or hidden coupling.

Control Plane boundary: this module manages handler registration only.
No computational work is performed here.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class TaskHandler(Protocol):
    """Protocol for all task handlers registered in the runtime.

    Data Plane contract: implementations execute computational work only.
    No lifecycle or coordination logic belongs in task handlers.
    """

    def run(self, payload: dict[str, Any]) -> Any:
        """Execute the task with the given payload.

        Args:
            payload: Input data for the task.

        Returns:
            Task result (any serializable value).

        """
        ...


class RegistryError(Exception):
    """Raised on task registry violations (duplicate name or missing task).

    Attributes:
        task: The task name that caused the error.
        reason: Human-readable explanation of the violation.

    """

    def __init__(self, task: str, reason: str) -> None:
        """Initialize with task name and reason.

        Args:
            task: Task name that caused the error.
            reason: Human-readable explanation of the violation.

        """
        super().__init__(f"Registry error for task '{task}': {reason}")
        self.task = task
        self.reason = reason


class TaskRegistry:
    """Maps task names to TaskHandler instances.

    Control Plane component: manages handler registration and lookup.
    All registered handlers must implement the TaskHandler protocol.
    """

    def __init__(self) -> None:
        """Initialize an empty task registry."""
        self._handlers: dict[str, TaskHandler] = {}
        logger.debug("TaskRegistry initialized")

    def register(self, name: str, handler: TaskHandler) -> None:
        """Register a handler under a task name.

        Args:
            name: Unique task identifier.
            handler: Object implementing the TaskHandler protocol.

        Raises:
            RegistryError: If the name is already registered.

        """
        if name in self._handlers:
            raise RegistryError(name, "task already registered")
        self._handlers[name] = handler
        logger.info("TaskRegistry: registered handler for task '%s'", name)

    def get(self, name: str) -> TaskHandler:
        """Retrieve the handler for a given task name.

        Args:
            name: Task identifier to look up.

        Returns:
            Registered TaskHandler for the given name.

        Raises:
            RegistryError: If no handler is registered for the task.

        """
        handler = self._handlers.get(name)
        if handler is None:
            raise RegistryError(name, "no handler registered")
        return handler

    def names(self) -> list[str]:
        """Return all registered task names in sorted order.

        Returns:
            Sorted list of registered task identifiers.

        """
        return sorted(self._handlers)

    def checkpoint(self) -> dict[str, Any]:
        """Serialize registry state for diagnostics.

        Returns:
            Dict with the list of registered task names.

        """
        return {"registered_tasks": self.names()}


__all__ = ["RegistryError", "TaskHandler", "TaskRegistry"]
