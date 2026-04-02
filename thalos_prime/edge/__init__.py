"""Thalos Prime - Deterministic Edge Executor subsystem (Data Plane).

Provides a bounded, deterministic execution wrapper for computational
work.  No lifecycle orchestration; explicit device selection and a
fixed-capacity task queue.  All operations are synchronous and
produce identical outputs for identical inputs.
"""

from thalos_prime.edge.executor import (
    DeviceType,
    EdgeExecutor,
    ExecutionResult,
    ExecutionTask,
)

__all__ = [
    "DeviceType",
    "EdgeExecutor",
    "ExecutionResult",
    "ExecutionTask",
]
