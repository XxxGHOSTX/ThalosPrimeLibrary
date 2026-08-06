"""Counterfactual evidence analysis and decision-flip discovery."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Sequence

from pydantic import BaseModel, ConfigDict, Field


class CounterfactualCase(BaseModel):
    """One minimal perturbation that changes the decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    removed_evidence: tuple[str, ...]
    remaining_evidence: tuple[str, ...]
    resulting_decision: str
    flip: bool
    minimal: bool


class CounterfactualReport(BaseModel):
    """Decision sensitivity surface for a fixed evidence set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_decision: str
    evidence_count: int = Field(ge=0)
    cases_examined: int = Field(ge=0)
    flip_cases: tuple[CounterfactualCase, ...]
    minimal_flip_cases: tuple[CounterfactualCase, ...]
    critical_evidence: tuple[str, ...]
    robust_evidence: tuple[str, ...]


@dataclass(frozen=True)
class CounterfactualEngine:
    """Search the local evidence neighborhood for decision-flipping changes."""

    max_removal_order: int = 2

    def analyze(
        self,
        *,
        evidence_ids: Sequence[str],
        baseline_decision: str,
        decide: Callable[[tuple[str, ...]], str],
    ) -> CounterfactualReport:
        base = tuple(sorted(set(evidence_ids)))
        examined = 0
        flip_cases: list[CounterfactualCase] = []
        for order in range(1, min(self.max_removal_order, len(base)) + 1):
            for removed in combinations(base, order):
                examined += 1
                removed_set = set(removed)
                remaining = tuple(item for item in base if item not in removed_set)
                decision = decide(remaining)
                flip = decision != baseline_decision
                case = CounterfactualCase(
                    removed_evidence=removed,
                    remaining_evidence=remaining,
                    resulting_decision=decision,
                    flip=flip,
                    minimal=False,
                )
                if flip:
                    flip_cases.append(case)

        minimal: list[CounterfactualCase] = []
        for case in flip_cases:
            if case.removed_evidence and not any(
                set(other.removed_evidence).issubset(set(case.removed_evidence))
                and len(other.removed_evidence) < len(case.removed_evidence)
                for other in flip_cases
            ):
                minimal.append(case.model_copy(update={"minimal": True}))

        critical: set[str] = set()
        for case in minimal:
            critical.update(case.removed_evidence)
        robust = set(base) - critical
        return CounterfactualReport(
            baseline_decision=baseline_decision,
            evidence_count=len(base),
            cases_examined=examined,
            flip_cases=tuple(flip_cases),
            minimal_flip_cases=tuple(minimal),
            critical_evidence=tuple(sorted(critical)),
            robust_evidence=tuple(sorted(robust)),
        )
