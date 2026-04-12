"""Autonomous background orchestration subsystem for Thalos Prime.

Exports the AutonomousOrchestrator and its companion public types so
callers can reference them without reaching into the implementation module.
"""

from thalos_prime.autonomous.orchestrator import (
    AutonomousOrchestrator,
    OrchestratorError,
    WorkerMetrics,
    WorkerSpec,
    get_orchestrator,
    start_orchestrator,
)

__all__ = [
    "AutonomousOrchestrator",
    "OrchestratorError",
    "WorkerMetrics",
    "WorkerSpec",
    "get_orchestrator",
    "start_orchestrator",
]
