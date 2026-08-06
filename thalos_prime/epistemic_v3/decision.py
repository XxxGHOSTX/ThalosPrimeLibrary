"""Policy-driven decision compilation for Thalos Prime epistemic transactions."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from thalos_prime.epistemic_v3.counterfactual import CounterfactualReport
from thalos_prime.epistemic_v3.lattice import BeliefPosition, DecisionState, InformationState
from thalos_prime.epistemic_v3.stability import StabilityReport


class DecisionReason(StrEnum):
    """Explicit reason codes for a compiled epistemic decision."""

    SUPPORT_SUFFICIENT = "support_sufficient"
    SUPPORT_INSUFFICIENT = "support_insufficient"
    CONTRADICTION_PRESENT = "contradiction_present"
    CHALLENGES_UNRESOLVED = "challenges_unresolved"
    STABILITY_LOW = "stability_low"
    CRITICAL_EVIDENCE = "critical_evidence"
    STABLE_AND_REDUNDANT = "stable_and_redundant"


class DecisionArtifact(BaseModel):
    """Auditable policy result derived from a belief position and sensitivity analyses."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str
    claim_id: str
    input_decision: DecisionState
    final_decision: DecisionState
    reasons: tuple[DecisionReason, ...]
    stability_score: float = Field(ge=0.0, le=1.0)
    reversibility_score: float = Field(ge=0.0, le=1.0)
    critical_evidence_count: int = Field(ge=0)
    minimum_flip_order: int | None = Field(default=None, ge=1)
    safe_to_state_as_fact: bool
    compiler_version: str = "decision-compiler-v1"


class DecisionCompiler:
    """Compile a final policy decision without changing the underlying evidence."""

    VERSION = "decision-compiler-v1"

    def __init__(
        self,
        *,
        minimum_stability: float = 0.75,
        stable_stability: float = 0.90,
        max_safe_flip_order: int = 1,
    ) -> None:
        self.minimum_stability = minimum_stability
        self.stable_stability = stable_stability
        self.max_safe_flip_order = max_safe_flip_order

    def compile(
        self,
        *,
        belief: BeliefPosition,
        stability: StabilityReport,
        counterfactual: CounterfactualReport,
    ) -> DecisionArtifact:
        reasons: list[DecisionReason] = []
        decision = belief.decision

        if belief.information_state is InformationState.BOTH or belief.contradiction_strength > 0.0:
            decision = DecisionState.DISPUTED
            reasons.append(DecisionReason.CONTRADICTION_PRESENT)

        if belief.unresolved_challenges > 0:
            if decision is DecisionState.ACCEPTED:
                decision = DecisionState.PROVISIONAL
            reasons.append(DecisionReason.CHALLENGES_UNRESOLVED)

        if stability.stability_score < self.minimum_stability:
            if decision is DecisionState.ACCEPTED:
                decision = DecisionState.PROVISIONAL
            reasons.append(DecisionReason.STABILITY_LOW)
        elif stability.stability_score >= self.stable_stability:
            reasons.append(DecisionReason.STABLE_AND_REDUNDANT)

        critical = len(counterfactual.critical_evidence)
        minimum_flip_order = min(
            (len(case.removed_evidence) for case in counterfactual.minimal_flip_cases),
            default=None,
        )
        if minimum_flip_order is not None and minimum_flip_order <= self.max_safe_flip_order:
            if decision is DecisionState.ACCEPTED:
                decision = DecisionState.PROVISIONAL
            reasons.append(DecisionReason.CRITICAL_EVIDENCE)

        if decision in {DecisionState.ACCEPTED, DecisionState.HISTORICAL_ACCEPTED}:
            reasons.append(DecisionReason.SUPPORT_SUFFICIENT)
        elif decision in {DecisionState.PENDING, DecisionState.REJECTED}:
            reasons.append(DecisionReason.SUPPORT_INSUFFICIENT)

        safe_to_state_as_fact = (
            decision is DecisionState.ACCEPTED
            and belief.information_state is InformationState.SUPPORT_ONLY
            and belief.unresolved_challenges == 0
            and stability.stability_score >= self.stable_stability
            and (minimum_flip_order is None or minimum_flip_order > self.max_safe_flip_order)
        )

        identity = {
            "claim_id": belief.claim_id,
            "input_decision": belief.decision.value,
            "final_decision": decision.value,
            "reasons": [reason.value for reason in reasons],
            "stability_score": stability.stability_score,
            "reversibility_score": stability.reversibility_score,
            "critical_evidence_count": critical,
            "minimum_flip_order": minimum_flip_order,
            "safe_to_state_as_fact": safe_to_state_as_fact,
            "compiler_version": self.VERSION,
        }
        digest = hashlib.sha256(
            json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return DecisionArtifact(
            decision_id=f"dec:{digest}",
            claim_id=belief.claim_id,
            input_decision=belief.decision,
            final_decision=decision,
            reasons=tuple(dict.fromkeys(reasons)),
            stability_score=stability.stability_score,
            reversibility_score=stability.reversibility_score,
            critical_evidence_count=critical,
            minimum_flip_order=minimum_flip_order,
            safe_to_state_as_fact=safe_to_state_as_fact,
        )
