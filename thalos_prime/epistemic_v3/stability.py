"""Perturbation stability and reversibility analysis."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field


class StabilityReport(BaseModel):
    """Decision stability under controlled evidence perturbations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_decision: str
    perturbation_count: int = Field(ge=0)
    changed_decision_count: int = Field(ge=0)
    stability_score: float = Field(ge=0.0, le=1.0)
    reversibility_score: float = Field(ge=0.0, le=1.0)
    perturbation_labels: tuple[str, ...] = ()
    changed_labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class Perturbation:
    """Named deterministic change to an evidence set."""

    label: str
    evidence_ids: tuple[str, ...]


class StabilityAnalyzer:
    """Measure how easily a conclusion changes under valid perturbations."""

    def analyze(
        self,
        *,
        evidence_ids: Sequence[str],
        baseline_decision: str,
        decide: Callable[[tuple[str, ...]], str],
        max_removals: int = 1,
    ) -> StabilityReport:
        base = tuple(sorted(set(evidence_ids)))
        perturbations = self._build_perturbations(base, max_removals=max_removals)
        changed: list[str] = []
        for perturbation in perturbations:
            decision = decide(perturbation.evidence_ids)
            if decision != baseline_decision:
                changed.append(perturbation.label)
        count = len(perturbations)
        changed_count = len(changed)
        stability = 1.0 if count == 0 else 1.0 - (changed_count / count)
        reversibility = 1.0 - stability
        return StabilityReport(
            baseline_decision=baseline_decision,
            perturbation_count=count,
            changed_decision_count=changed_count,
            stability_score=round(stability, 6),
            reversibility_score=round(reversibility, 6),
            perturbation_labels=tuple(p.label for p in perturbations),
            changed_labels=tuple(changed),
        )

    @staticmethod
    def _build_perturbations(evidence_ids: tuple[str, ...], max_removals: int) -> tuple[Perturbation, ...]:
        if max_removals < 1:
            return ()
        perturbations: list[Perturbation] = []
        for size in range(1, min(max_removals, len(evidence_ids)) + 1):
            for subset in combinations(evidence_ids, size):
                removed = set(subset)
                remaining = tuple(item for item in evidence_ids if item not in removed)
                label = "remove:" + ",".join(subset)
                perturbations.append(Perturbation(label=label, evidence_ids=remaining))
        perturbations.append(Perturbation(label="reorder:reverse", evidence_ids=tuple(reversed(evidence_ids))))
        return tuple(perturbations)
