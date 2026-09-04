from __future__ import annotations

from collections.abc import Iterable
from statistics import fmean

from .models import CognitiveObservation, CognitiveScore, Prediction


class RecursiveInformationEngine:
    """Measure predictive, reflective, consistency, and efficiency signals.

    The engine is deliberately substrate-neutral. It evaluates observations
    supplied by a runner and never treats a score as evidence of consciousness.
    """

    def score(
        self,
        observation: CognitiveObservation,
        history: Iterable[CognitiveObservation] = (),
    ) -> CognitiveScore:
        prior = tuple(history)
        accuracy = observation.prediction_accuracy
        consistency = observation.self_model.consistency
        contradiction_rate = min(1.0, observation.contradictions / max(1, len(observation.predictions)))
        calibration = max(0.0, 1.0 - observation.calibration_error)

        if not prior:
            memory_stability = consistency
        else:
            memory_stability = self._state_stability(prior + (observation,))

        efficiency = accuracy / observation.operation_cost
        composite = (
            0.30 * accuracy
            + 0.25 * consistency
            + 0.15 * memory_stability
            + 0.15 * (1.0 - contradiction_rate)
            + 0.10 * calibration
            + 0.05 * min(1.0, efficiency)
        )
        return CognitiveScore(
            prediction_accuracy=accuracy,
            self_model_consistency=consistency,
            memory_stability=memory_stability,
            contradiction_rate=contradiction_rate,
            calibration=calibration,
            efficiency=efficiency,
            composite=composite,
        )

    @staticmethod
    def _state_stability(observations: tuple[CognitiveObservation, ...]) -> float:
        snapshots = [o.self_model.state for o in observations]
        if len(snapshots) < 2:
            return 1.0
        keys = sorted(set().union(*(set(s) for s in snapshots)))
        if not keys:
            return 1.0
        stable = sum(
            len({s.get(k) for s in snapshots}) == 1
            for k in keys
        )
        return stable / len(keys)

    @staticmethod
    def compare(baseline: CognitiveScore, candidate: CognitiveScore) -> dict[str, float]:
        """Return candidate-minus-baseline deltas for deterministic promotion logic."""
        return {
            key: candidate.as_dict()[key] - baseline.as_dict()[key]
            for key in baseline.as_dict()
        }
