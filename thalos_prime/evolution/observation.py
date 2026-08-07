"""Runtime introspection and adaptive routing for THALOS Prime."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .registry import ModuleRegistry


@dataclass(frozen=True)
class Observation:
    failure_rate: float
    latency: float
    efficiency: float
    slow_component: str | None
    recommendation: str | None
    evidence: dict[str, Any]


class SelfObserver:
    """Turns execution telemetry into explicit optimization signals."""

    def analyze(self, metrics: dict[str, dict[str, float]]) -> Observation:
        if not metrics:
            return Observation(0.0, 0.0, 1.0, None, None, {})
        slow = max(metrics, key=lambda key: metrics[key].get("latency", 0.0))
        failure = sum(v.get("failure_rate", 0.0) for v in metrics.values()) / len(metrics)
        latency = sum(v.get("latency", 0.0) for v in metrics.values()) / len(metrics)
        efficiency = sum(v.get("efficiency", 0.0) for v in metrics.values()) / len(metrics)
        recommendation = f"replace or optimize {slow}" if metrics[slow].get("latency", 0.0) > latency else None
        return Observation(failure, latency, efficiency, slow, recommendation, metrics)


class RuntimeRouter:
    """Selects the active proven module while preserving explicit versioning."""

    def __init__(self, registry: ModuleRegistry) -> None:
        self.registry = registry

    def select(self, module: str) -> Any:
        return self.registry.get(module).handler

    def version(self, module: str) -> str:
        return self.registry.active_version(module)
