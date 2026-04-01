"""Deterministic edge runtime abstraction for ThalosPrime Library.

Data Plane module: provides a deterministic execution wrapper for
computational work. No lifecycle orchestration, no unbounded concurrency.
Explicit device selection and bounded execution queue.

This module MUST NOT contain lifecycle coordination logic.
"""

from __future__ import annotations

import hashlib
import logging
from collections import deque
from enum import StrEnum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DeviceType(StrEnum):
    """Target compute device for task execution.

    Members:
        CPU: Execute on the central processing unit.
        GPU: Execute on a graphics processing unit.
        NPU: Execute on a neural processing unit.
        AUTO: Automatically select the best available device.

    """

    CPU = "cpu"
    GPU = "gpu"
    NPU = "npu"
    AUTO = "auto"


class ExecutionResult(BaseModel):
    """The outcome of a single task execution.

    Attributes:
        task_id: Identifier of the task that was executed.
        device: The device on which the task ran.
        success: ``True`` when the task completed without error.
        result: Serialised string output, or ``None`` on failure.
        error: Error description, or ``None`` on success.
        duration_ns: Wall-clock nanoseconds spent executing.
        timestamp_ns: Nanosecond timestamp when execution was requested.
        seed: Randomness seed used, if any.

    """

    task_id: str
    device: DeviceType
    success: bool
    result: str | None = None
    error: str | None = None
    duration_ns: int
    timestamp_ns: int
    seed: str | None = None


class ExecutionTask(BaseModel):
    """A single unit of work to be executed by an :class:`EdgeExecutor`.

    Attributes:
        task_id: Unique identifier for this task.
        operation: Name of the operation to perform (``echo``, ``hash``,
            ``count``).
        payload: Operation-specific key/value string data.
        device: Target device; defaults to ``DeviceType.CPU``.
        seed: Optional determinism seed for the operation.
        timeout_ns: Maximum allowed execution time in nanoseconds (30 s default).

    """

    task_id: str
    operation: str
    payload: dict[str, str] = Field(default_factory=dict)
    device: DeviceType = DeviceType.CPU
    seed: str | None = None
    timeout_ns: int = 30_000_000_000


class EdgeExecutor:
    """Deterministic bounded-queue edge executor.

    Accepts :class:`ExecutionTask` instances into a fixed-capacity queue and
    dispatches them synchronously via :meth:`execute` or :meth:`execute_queued`.

    Supported operations:

    * ``echo``: returns ``payload["message"]``
    * ``hash``: returns SHA-256 hex digest of ``payload["content"]``
    * ``count``: returns ``str(len(payload.get("content", "")))``

    Any other operation name raises :class:`ValueError`.

    This is a **Data Plane** class and deliberately omits lifecycle methods.
    """

    def __init__(
        self,
        executor_id: str,
        max_queue_size: int = 100,
        device: DeviceType = DeviceType.CPU,
    ) -> None:
        """Initialise the edge executor with a bounded task queue.

        Args:
            executor_id: Deterministic string identifier for this executor.
            max_queue_size: Maximum number of queued tasks; defaults to 100.
            device: Default device for task execution.

        """
        self._executor_id = executor_id
        self._device = device
        self._max_queue_size = max_queue_size
        self._queue: deque[ExecutionTask] = deque(maxlen=max_queue_size)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def executor_id(self) -> str:
        """Deterministic string identifier for this executor instance.

        Returns:
            The executor ID supplied at construction time.

        """
        return self._executor_id

    @property
    def device(self) -> DeviceType:
        """Default compute device for this executor.

        Returns:
            The :class:`DeviceType` supplied at construction time.

        """
        return self._device

    @property
    def queue_size(self) -> int:
        """Number of tasks currently waiting in the queue.

        Returns:
            Integer count of queued tasks.

        """
        return len(self._queue)

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def submit(self, task: ExecutionTask) -> str:
        """Add *task* to the bounded execution queue.

        Args:
            task: The :class:`ExecutionTask` to enqueue.

        Returns:
            The ``task_id`` of the submitted task.

        Raises:
            OverflowError: When the queue has reached its capacity.

        """
        if len(self._queue) >= self._max_queue_size:
            msg = "execution queue is full"
            raise OverflowError(msg)
        self._queue.append(task)
        logger.debug(
            "EdgeExecutor(%s) queued task_id=%s (queue_size=%d)",
            self._executor_id,
            task.task_id,
            len(self._queue),
        )
        return task.task_id

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, task: ExecutionTask, timestamp_ns: int) -> ExecutionResult:
        """Execute *task* deterministically and return the result.

        Operations:

        * ``echo``: returns ``payload.get("message", "")``
        * ``hash``: returns SHA-256 hex digest of ``payload.get("content", "")``
        * ``count``: returns ``str(len(payload.get("content", "")))``

        Args:
            task: The :class:`ExecutionTask` to execute.
            timestamp_ns: Nanosecond timestamp for the result record.

        Returns:
            An :class:`ExecutionResult` with ``success=True`` and the
            serialised output.

        Raises:
            ValueError: When ``task.operation`` is not a recognised operation.

        """
        if task.operation == "echo":
            result_str = task.payload.get("message", "")
        elif task.operation == "hash":
            content = task.payload.get("content", "")
            result_str = hashlib.sha256(content.encode("utf-8")).hexdigest()
        elif task.operation == "count":
            result_str = str(len(task.payload.get("content", "")))
        else:
            msg = f"unknown operation: {task.operation!r}"
            raise ValueError(msg)

        logger.debug(
            "EdgeExecutor(%s) executed task_id=%s operation=%r",
            self._executor_id,
            task.task_id,
            task.operation,
        )
        return ExecutionResult(
            task_id=task.task_id,
            device=task.device,
            success=True,
            result=result_str,
            error=None,
            duration_ns=0,
            timestamp_ns=timestamp_ns,
            seed=task.seed,
        )

    def execute_queued(self, timestamp_ns: int) -> list[ExecutionResult]:
        """Drain the queue and execute all pending tasks in FIFO order.

        Tasks that raise :class:`ValueError` are captured as failed results
        rather than propagating the exception; this ensures all queued tasks
        are attempted.

        Args:
            timestamp_ns: Nanosecond timestamp applied to every result.

        Returns:
            Ordered list of :class:`ExecutionResult` instances, one per task.

        """
        results: list[ExecutionResult] = []
        while self._queue:
            task = self._queue.popleft()
            try:
                result = self.execute(task, timestamp_ns)
            except ValueError as exc:
                result = ExecutionResult(
                    task_id=task.task_id,
                    device=task.device,
                    success=False,
                    result=None,
                    error=str(exc),
                    duration_ns=0,
                    timestamp_ns=timestamp_ns,
                    seed=task.seed,
                )
            results.append(result)
        return results


__all__ = [
    "DeviceType",
    "EdgeExecutor",
    "ExecutionResult",
    "ExecutionTask",
]
