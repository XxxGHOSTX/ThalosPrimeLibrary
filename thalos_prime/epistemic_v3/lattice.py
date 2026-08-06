"""Multi-axis belief lattice and decision classification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from thalos_prime.epistemic_v3.warrant import Warrant


class InformationState(StrEnum):
    """Information completeness relative to support and contradiction."""

    UNKNOWN = "unknown"
    SUPPORT_ONLY = "support_only"
    CONTRADICTION_ONLY = "contradiction_only"
    BOTH = "both"


class StabilityState(StrEnum):
    """Sensitivity of a decision to removal or perturbation of evidence."""

    UNKNOWN = "unknown"
    FRAGILE = "fragile"
    MODERATE = "moderate"
    STABLE = "stable"


class TemporalState(StrEnum):
    """Temporal applicability of a claim."""

    UNSCOPED = "unscoped"
    CURRENT = "current"
    HISTORICAL = "historical"
    EXPIRED = "expired"
    CONFLICTED = "conflicted"


class DecisionState(StrEnum):
    """Policy decision independent of world-truth semantics."""

    PENDING = "pending"
    PROVISIONAL = "provisional"
    ACCEPTED = "accepted"
    DISPUTED = "disputed"
    REJECTED = "rejected"
    HISTORICAL_ACCEPTED = "historical_accepted"


class BeliefPosition(BaseModel):
    """A point in the multidimensional belief lattice."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    information_state: InformationState
    support_strength: float = Field(ge=0.0, le=1.0)
    contradiction_strength: float = Field(ge=0.0, le=1.0)
    independence: float = Field(ge=0.0, le=1.0)
    stability: StabilityState
    temporal: TemporalState
    decision: DecisionState
    reversibility: float = Field(ge=0.0, le=1.0)
    unresolved_challenges: int = Field(ge=0)

    @property
    def epistemically_safe_to_state_as_fact(self) -> bool:
        return (
            self.decision is DecisionState.ACCEPTED
            and self.information_state is InformationState.SUPPORT_ONLY
            and self.stability is StabilityState.STABLE
            and self.unresolved_challenges == 0
        )


@dataclass(frozen=True)
class LatticeThresholds:
    """Explicit policy thresholds for classification."""

    accept_support: float = 0.80
    provisional_support: float = 0.55
    dispute_contradiction: float = 0.55
    stable_support: float = 0.80
    moderate_support: float = 0.55
    low_reversibility: float = 0.30


class BeliefLattice:
    """Classify claims without collapsing epistemic dimensions into one score."""

    def __init__(self, thresholds: LatticeThresholds | None = None) -> None:
        self.thresholds = thresholds or LatticeThresholds()

    def classify(
        self,
        *,
        claim_id: str,
        warrant: Warrant,
        challenge_count: int,
        resolved_challenge_count: int,
        failed_challenge_count: int,
        temporal: TemporalState = TemporalState.UNSCOPED,
        stability: StabilityState | None = None,
    ) -> BeliefPosition:
        if warrant.support > 0 and warrant.contradiction > 0:
            information = InformationState.BOTH
        elif warrant.support > 0:
            information = InformationState.SUPPORT_ONLY
        elif warrant.contradiction > 0:
            information = InformationState.CONTRADICTION_ONLY
        else:
            information = InformationState.UNKNOWN

        if stability is None:
            stability = self._infer_stability(warrant)

        unresolved = max(0, challenge_count - resolved_challenge_count - failed_challenge_count)
        if information is InformationState.BOTH or warrant.contradiction >= self.thresholds.dispute_contradiction:
            decision = DecisionState.DISPUTED
        elif warrant.support >= self.thresholds.accept_support and failed_challenge_count == 0 and unresolved == 0:
            decision = DecisionState.ACCEPTED
        elif warrant.support >= self.thresholds.provisional_support:
            decision = DecisionState.PROVISIONAL
        else:
            decision = DecisionState.PENDING

        if temporal is TemporalState.EXPIRED and decision is DecisionState.ACCEPTED:
            decision = DecisionState.HISTORICAL_ACCEPTED

        reversibility = self._reversibility(warrant, stability, unresolved)
        return BeliefPosition(
            claim_id=claim_id,
            information_state=information,
            support_strength=round(warrant.support, 6),
            contradiction_strength=round(warrant.contradiction, 6),
            independence=round(warrant.independence, 6),
            stability=stability,
            temporal=temporal,
            decision=decision,
            reversibility=round(reversibility, 6),
            unresolved_challenges=unresolved,
        )

    def _infer_stability(self, warrant: Warrant) -> StabilityState:
        support = warrant.usable_support
        if support >= self.thresholds.stable_support and warrant.independence >= self.thresholds.stable_support:
            return StabilityState.STABLE
        if support >= self.thresholds.moderate_support:
            return StabilityState.MODERATE
        return StabilityState.FRAGILE

    @staticmethod
    def _reversibility(warrant: Warrant, stability: StabilityState, unresolved: int) -> float:
        stability_penalty = {
            StabilityState.STABLE: 0.15,
            StabilityState.MODERATE: 0.45,
            StabilityState.FRAGILE: 0.80,
            StabilityState.UNKNOWN: 0.95,
        }[stability]
        challenge_penalty = min(0.50, unresolved * 0.10)
        return max(0.0, min(1.0, stability_penalty + challenge_penalty + (1.0 - warrant.independence) * 0.25))
