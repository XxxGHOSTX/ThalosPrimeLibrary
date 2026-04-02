"""Tests for the deterministic EdgeExecutor subsystem (Data Plane).

Covers DeviceType, ExecutionResult, ExecutionTask, and EdgeExecutor
including happy path, operation dispatch, queue management, error
handling, and batch execution.  All tests use deterministic, fixed inputs.
"""

from __future__ import annotations

import hashlib

import pytest

from thalos_prime.edge.executor import (
    DeviceType,
    EdgeExecutor,
    ExecutionResult,
    ExecutionTask,
)

# ---------------------------------------------------------------------------
# Fixed test constants
# ---------------------------------------------------------------------------
_TS = 1_700_000_000_000_000_000  # Fixed nanosecond timestamp


def _make_executor(
    executor_id: str = "exec-001",
    max_queue_size: int = 10,
    device: DeviceType = DeviceType.CPU,
) -> EdgeExecutor:
    return EdgeExecutor(
        executor_id=executor_id,
        max_queue_size=max_queue_size,
        device=device,
    )


def _make_task(
    task_id: str = "task-001",
    operation: str = "echo",
    payload: dict[str, str] | None = None,
    device: DeviceType = DeviceType.CPU,
) -> ExecutionTask:
    effective_payload = {"message": "hello"} if payload is None else payload
    return ExecutionTask(
        task_id=task_id,
        operation=operation,
        payload=effective_payload,
        device=device,
    )


# ===========================================================================
# DeviceType
# ===========================================================================


class TestDeviceType:
    def test_all_members_present(self) -> None:
        members = set(DeviceType)
        assert DeviceType.CPU in members
        assert DeviceType.GPU in members
        assert DeviceType.NPU in members
        assert DeviceType.AUTO in members

    def test_is_str(self) -> None:
        assert isinstance(DeviceType.CPU, str)

    def test_values(self) -> None:
        assert DeviceType.CPU.value == "cpu"
        assert DeviceType.AUTO.value == "auto"


# ===========================================================================
# ExecutionTask
# ===========================================================================


class TestExecutionTask:
    def test_fields_round_trip(self) -> None:
        task = ExecutionTask(
            task_id="t1",
            operation="echo",
            payload={"message": "hi"},
            device=DeviceType.GPU,
            seed="s1",
            timeout_ns=5_000_000_000,
        )
        assert task.task_id == "t1"
        assert task.operation == "echo"
        assert task.payload == {"message": "hi"}
        assert task.device is DeviceType.GPU
        assert task.seed == "s1"
        assert task.timeout_ns == 5_000_000_000

    def test_defaults(self) -> None:
        task = ExecutionTask(task_id="t2", operation="hash")
        assert task.device is DeviceType.CPU
        assert task.seed is None
        assert task.timeout_ns == 30_000_000_000
        assert task.payload == {}

    def test_serialisation_round_trip(self) -> None:
        task = ExecutionTask(
            task_id="t3",
            operation="count",
            payload={"content": "hello world"},
        )
        data = task.model_dump()
        restored = ExecutionTask.model_validate(data)
        assert restored == task


# ===========================================================================
# ExecutionResult
# ===========================================================================


class TestExecutionResult:
    def test_successful_result(self) -> None:
        result = ExecutionResult(
            task_id="t1",
            device=DeviceType.CPU,
            success=True,
            result="42",
            error=None,
            duration_ns=0,
            timestamp_ns=_TS,
        )
        assert result.success is True
        assert result.result == "42"
        assert result.error is None

    def test_failed_result(self) -> None:
        result = ExecutionResult(
            task_id="t2",
            device=DeviceType.CPU,
            success=False,
            result=None,
            error="unknown operation",
            duration_ns=0,
            timestamp_ns=_TS,
        )
        assert result.success is False
        assert result.result is None
        assert result.error == "unknown operation"

    def test_serialisation_round_trip(self) -> None:
        result = ExecutionResult(
            task_id="t3",
            device=DeviceType.NPU,
            success=True,
            result="output",
            error=None,
            duration_ns=1000,
            timestamp_ns=_TS,
            seed="seed-xyz",
        )
        data = result.model_dump()
        restored = ExecutionResult.model_validate(data)
        assert restored == result


# ===========================================================================
# EdgeExecutor - properties
# ===========================================================================


class TestEdgeExecutorProperties:
    def test_executor_id(self) -> None:
        exec_ = _make_executor("my-executor")
        assert exec_.executor_id == "my-executor"

    def test_device(self) -> None:
        exec_ = _make_executor(device=DeviceType.GPU)
        assert exec_.device is DeviceType.GPU

    def test_queue_size_initially_zero(self) -> None:
        exec_ = _make_executor()
        assert exec_.queue_size == 0

    def test_queue_size_after_submit(self) -> None:
        exec_ = _make_executor()
        exec_.submit(_make_task())
        assert exec_.queue_size == 1


# ===========================================================================
# EdgeExecutor - submit
# ===========================================================================


class TestEdgeExecutorSubmit:
    def test_submit_returns_task_id(self) -> None:
        exec_ = _make_executor()
        task = _make_task("task-xyz")
        returned = exec_.submit(task)
        assert returned == "task-xyz"

    def test_submit_multiple_tasks(self) -> None:
        exec_ = _make_executor(max_queue_size=5)
        for i in range(5):
            exec_.submit(_make_task(f"t{i}"))
        assert exec_.queue_size == 5

    def test_submit_full_queue_raises_overflow(self) -> None:
        exec_ = _make_executor(max_queue_size=2)
        exec_.submit(_make_task("t1"))
        exec_.submit(_make_task("t2"))
        with pytest.raises(OverflowError):
            exec_.submit(_make_task("t3"))

    def test_submit_after_drain_succeeds(self) -> None:
        exec_ = _make_executor(max_queue_size=1)
        exec_.submit(_make_task("t1"))
        exec_.execute_queued(_TS)
        exec_.submit(_make_task("t2"))
        assert exec_.queue_size == 1


# ===========================================================================
# EdgeExecutor - execute operations
# ===========================================================================


class TestEdgeExecutorExecute:
    def test_echo_operation(self) -> None:
        exec_ = _make_executor()
        task = _make_task(operation="echo", payload={"message": "hello world"})
        result = exec_.execute(task, _TS)
        assert result.success is True
        assert result.result == "hello world"

    def test_echo_empty_message(self) -> None:
        exec_ = _make_executor()
        task = _make_task(operation="echo", payload={})
        result = exec_.execute(task, _TS)
        assert result.success is True
        assert result.result == ""

    def test_hash_operation(self) -> None:
        exec_ = _make_executor()
        content = "deterministic content"
        task = _make_task(operation="hash", payload={"content": content})
        result = exec_.execute(task, _TS)
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert result.success is True
        assert result.result == expected

    def test_hash_empty_content(self) -> None:
        exec_ = _make_executor()
        task = _make_task(operation="hash", payload={})
        result = exec_.execute(task, _TS)
        expected = hashlib.sha256(b"").hexdigest()
        assert result.result == expected

    def test_count_operation(self) -> None:
        exec_ = _make_executor()
        task = _make_task(operation="count", payload={"content": "hello"})
        result = exec_.execute(task, _TS)
        assert result.success is True
        assert result.result == "5"

    def test_count_empty_content(self) -> None:
        exec_ = _make_executor()
        task = _make_task(operation="count", payload={})
        result = exec_.execute(task, _TS)
        assert result.result == "0"

    def test_unknown_operation_raises(self) -> None:
        exec_ = _make_executor()
        task = _make_task(operation="fly-to-moon")
        with pytest.raises(ValueError):
            exec_.execute(task, _TS)

    def test_result_carries_correct_task_id(self) -> None:
        exec_ = _make_executor()
        task = _make_task("unique-id-999")
        result = exec_.execute(task, _TS)
        assert result.task_id == "unique-id-999"

    def test_result_carries_correct_device(self) -> None:
        exec_ = _make_executor()
        task = _make_task(device=DeviceType.NPU)
        result = exec_.execute(task, _TS)
        assert result.device is DeviceType.NPU

    def test_result_carries_timestamp(self) -> None:
        exec_ = _make_executor()
        task = _make_task()
        result = exec_.execute(task, _TS)
        assert result.timestamp_ns == _TS

    def test_result_carries_seed(self) -> None:
        exec_ = _make_executor()
        task = ExecutionTask(
            task_id="t1",
            operation="echo",
            payload={"message": "hi"},
            seed="fixed-seed",
        )
        result = exec_.execute(task, _TS)
        assert result.seed == "fixed-seed"

    def test_determinism(self) -> None:
        exec1 = _make_executor()
        exec2 = _make_executor()
        task = _make_task(operation="hash", payload={"content": "same input"})
        r1 = exec1.execute(task, _TS)
        r2 = exec2.execute(task, _TS)
        assert r1.result == r2.result
        assert r1.success == r2.success


# ===========================================================================
# EdgeExecutor - execute_queued
# ===========================================================================


class TestEdgeExecutorExecuteQueued:
    def test_empty_queue_returns_empty(self) -> None:
        exec_ = _make_executor()
        results = exec_.execute_queued(_TS)
        assert results == []

    def test_drains_all_tasks(self) -> None:
        exec_ = _make_executor()
        for i in range(3):
            exec_.submit(_make_task(f"t{i}", operation="echo", payload={"message": f"msg{i}"}))
        results = exec_.execute_queued(_TS)
        assert len(results) == 3
        assert exec_.queue_size == 0

    def test_results_in_fifo_order(self) -> None:
        exec_ = _make_executor()
        for i in range(3):
            exec_.submit(_make_task(f"t{i}", operation="echo", payload={"message": f"msg{i}"}))
        results = exec_.execute_queued(_TS)
        assert results[0].task_id == "t0"
        assert results[1].task_id == "t1"
        assert results[2].task_id == "t2"

    def test_failed_tasks_captured_not_raised(self) -> None:
        exec_ = _make_executor()
        exec_.submit(_make_task("ok", operation="echo", payload={"message": "hi"}))
        exec_.submit(_make_task("bad", operation="unknown-op"))
        results = exec_.execute_queued(_TS)
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error is not None

    def test_queue_empty_after_execute_queued(self) -> None:
        exec_ = _make_executor()
        exec_.submit(_make_task())
        exec_.execute_queued(_TS)
        assert exec_.queue_size == 0
