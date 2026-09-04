from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Prediction:
    """A prediction and its observed outcome."""

    predicted: str
    observed: str
    confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")

    @property
    def correct(self) -> bool:
        return self.predicted == self.observed


@dataclass(frozen=True)
class SelfModelSnapshot:
    """Externally supplied model of the system's own state."""

    state: Mapping[str, str]
    predicted_state: Mapping[str, str]

    @property
    def consistency(self) -> float:
        keys = sorted(set(self.state) | set(self.predicted_state))
        if not keys:
            return 1.0
        return sum(self.state.get(k) == self.predicted_state.get(k) for k in keys) / len(keys)


@dataclass(frozen=True)
class CognitiveObservation:
    """One deterministic evaluation window."""

    observation_id: str
    predictions: tuple[Prediction, ...]
    self_model: SelfModelSnapshot
    contradictions: int = 0
    operation_cost: int = 1

    def __post_init__(self) -> None:
        if self.contradictions < 0:
            raise ValueError("contradictions must be >= 0")
        if self.operation_cost <= 0:
            raise ValueError("operation_cost must be > 0")

    @property
    def prediction_accuracy(self) -> float:
        if not self.predictions:
            return 0.0
        return sum(p.correct for p in self.predictions) / len(self.predictions)

    @property
    def calibration_error(self) -> float:
        if not self.predictions:
            return 1.0
        return sum(abs(p.confidence - float(p.correct)) for p in self.predictions) / len(self.predictions)


@dataclass(frozen=True)
class CognitiveScore:
    """A normalized, reproducible score; not a consciousness measurement."""

    prediction_accuracy: float
    self_model_consistency: float
    memory_stability: float
    contradiction_rate: float
    calibration: float
    efficiency: float
    composite: float

    def as_dict(self) -> dict[str, float]:
        return {
            "prediction_accuracy": self.prediction_accuracy,
            "self_model_consistency": self.self_model_consistency,
            "memory_stability": self.memory_stability,
            "contradiction_rate": self.contradiction_rate,
            "calibration": self.calibration,
            "efficiency": self.efficiency,
            "composite": self.composite,
        }
