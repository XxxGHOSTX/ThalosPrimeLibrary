"""Falsification shadows and adversarial challenge planning."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from thalos_prime.epistemic_v3.claim_ir import ClaimIR, ClaimType
from thalos_prime.epistemic_v3.warrant import Warrant


class ChallengeKind(StrEnum):
    """Kinds of challenge generated for a claim."""

    COUNTEREVIDENCE = "counterevidence"
    SOURCE_DEPENDENCE = "source_dependence"
    TEMPORAL = "temporal"
    SCOPE = "scope"
    ALTERNATIVE_EXPLANATION = "alternative_explanation"
    IDENTITY = "identity"
    CAUSAL = "causal"
    MEASUREMENT = "measurement"


class ChallengeTask(BaseModel):
    """A deterministic challenge request that another component can execute."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    kind: ChallengeKind
    question: str
    target_claim_id: str
    priority: int = Field(ge=1, le=10)
    required: bool = True


class ChallengePlan(BaseModel):
    """Complete falsification shadow for one claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_id: str
    claim_id: str
    tasks: tuple[ChallengeTask, ...]
    falsification_conditions: tuple[str, ...]
    generated_by: str = "challenge-engine-v1"

    @property
    def required_task_count(self) -> int:
        return sum(1 for task in self.tasks if task.required)


@dataclass(frozen=True)
class ChallengeOutcome:
    """Result of running a challenge task against existing warrant."""

    task_id: str
    passed: bool
    severity: float
    explanation: str


class ChallengeEngine:
    """Create and score falsification plans without assuming the claim is true."""

    VERSION = "challenge-engine-v1"

    @classmethod
    def build_plan(cls, claim: ClaimIR) -> ChallengePlan:
        tasks: list[ChallengeTask] = [
            cls._task(claim, ChallengeKind.COUNTEREVIDENCE, "What credible evidence would directly contradict this claim?", 10),
            cls._task(claim, ChallengeKind.SOURCE_DEPENDENCE, "Are the supporting witnesses causally dependent on one another?", 9),
            cls._task(claim, ChallengeKind.TEMPORAL, "Could the evidence be valid for a different time interval than the claim?", 8),
            cls._task(claim, ChallengeKind.SCOPE, "Does the evidence support the exact scope, population, quantity, or location asserted?", 8),
        ]
        conditions = [
            "A credible counter-witness directly entailing the negation of the claim.",
            "The principal supporting witnesses collapse into one causal lineage.",
            "The evidence is temporally invalid for the claim's stated interval.",
            "The evidence supports a narrower proposition than the claim being evaluated.",
        ]

        if claim.claim_type is ClaimType.CAUSAL:
            tasks.append(cls._task(
                claim,
                ChallengeKind.ALTERNATIVE_EXPLANATION,
                "What plausible competing cause could explain the observed outcome?",
                10,
            ))
            tasks.append(cls._task(
                claim,
                ChallengeKind.CAUSAL,
                "Is temporal order being mistaken for causation, and are confounders controlled?",
                10,
            ))
            conditions.extend([
                "A competing causal explanation accounts for the outcome at least as well.",
                "The evidence establishes correlation or sequence but not causal identification.",
            ])
        elif claim.claim_type is ClaimType.IDENTITY:
            tasks.append(cls._task(
                claim,
                ChallengeKind.IDENTITY,
                "Could the evidence refer to a different entity with the same or similar identifier?",
                10,
            ))
            conditions.append("The source identity cannot be uniquely bound to the target entity.")
        elif claim.claim_type is ClaimType.STATISTICAL:
            tasks.append(cls._task(
                claim,
                ChallengeKind.MEASUREMENT,
                "Could measurement error, sampling bias, or denominator choice reverse the conclusion?",
                9,
            ))
            conditions.append("A measurement or sampling artifact plausibly explains the observed result.")

        normalized_tasks = tuple(sorted(tasks, key=lambda task: (-task.priority, task.task_id)))
        payload = {
            "claim_id": claim.claim_id,
            "tasks": [task.model_dump(mode="json") for task in normalized_tasks],
            "conditions": conditions,
            "version": cls.VERSION,
        }
        plan_id = "chlg:" + hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return ChallengePlan(
            plan_id=plan_id,
            claim_id=claim.claim_id,
            tasks=normalized_tasks,
            falsification_conditions=tuple(conditions),
            generated_by=cls.VERSION,
        )

    @classmethod
    def assess_warrant(
        cls,
        plan: ChallengePlan,
        warrant: Warrant,
        *,
        completed_task_ids: Iterable[str] = (),
        failed_task_ids: Iterable[str] = (),
    ) -> tuple[ChallengeOutcome, ...]:
        completed = set(completed_task_ids)
        failed = set(failed_task_ids)
        outcomes: list[ChallengeOutcome] = []
        for task in plan.tasks:
            if task.task_id in failed:
                outcomes.append(ChallengeOutcome(task.task_id, False, 1.0, "Challenge produced a material failure."))
                continue
            if task.task_id in completed:
                outcomes.append(ChallengeOutcome(task.task_id, True, 0.0, "Challenge completed without finding a disqualifying condition."))
                continue
            severity = 1.0 - warrant.falsifiability
            outcomes.append(ChallengeOutcome(
                task.task_id,
                False,
                round(severity, 6),
                "Challenge remains unresolved; the claim is not fully falsified, but its vulnerability is untested.",
            ))
        return tuple(outcomes)

    @classmethod
    def _task(cls, claim: ClaimIR, kind: ChallengeKind, question: str, priority: int) -> ChallengeTask:
        raw = f"{cls.VERSION}|{claim.claim_id}|{kind.value}|{question}"
        task_id = "task:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return ChallengeTask(
            task_id=task_id,
            kind=kind,
            question=question,
            target_claim_id=claim.claim_id,
            priority=priority,
        )
