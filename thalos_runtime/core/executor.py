"""Task executor - Data Plane execution for thalos_runtime.

Executes registered TaskHandlers with explicit, typed error handling.
All computation is delegated to the handler; the executor only manages
invocation, logging, and error wrapping.

Data Plane boundary: no lifecycle coordination or control-plane logic
belongs here.  The executor must not mutate registry or memory state.
"""

from __future__ import annotations

import logging
from typing import Any

from thalos_runtime.core.registry import RegistryError, TaskRegistry

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Raised when a task handler raises an exception during execution.

    Attributes:
        task: The task name that failed.
        cause: The underlying exception that triggered this error.
    """

    def __init__(self, task: str, cause: Exception) -> None:
        """Initialize with task name and cause.

        Args:
            task: Task name that failed.
            cause: Underlying exception raised by the handler.
        """
        super().__init__(f"Execution of task '{task}' failed: {cause}")
        self.task = task
        self.cause = cause


class TaskExecutor:
    """Executes tasks from a TaskRegistry.

    Data Plane component: pure invocation and error handling.
    Does not perform lifecycle management or state storage.
    """

    def __init__(self, registry: TaskRegistry) -> None:
        """Initialize the executor with a task registry.

        Args:
            registry: Registry providing handler lookup.
        """
        self._registry = registry
        logger.debug("TaskExecutor initialized")

    def execute(self, task: str, payload: dict[str, Any]) -> Any:
        """Execute a registered task with the given payload.

        Args:
            task: Task name to execute.
            payload: Input data passed verbatim to the handler.

        Returns:
            Result produced by the task handler.

        Raises:
            RegistryError: If the task is not registered.
            ExecutionError: If the handler raises any exception.
        """
        handler = self._registry.get(task)
        logger.info("TaskExecutor: executing task '%s'", task)
        try:
            result = handler.run(payload)
        except RegistryError:
            raise
        except Exception as exc:
            logger.error(
                "TaskExecutor: task '%s' failed with %s: %s",
                task,
                type(exc).__name__,
                exc,
            )
            raise ExecutionError(task, exc) from exc
        logger.info("TaskExecutor: task '%s' completed successfully", task)
        return result


__all__ = ["ExecutionError", "TaskExecutor"]
