"""Falsifiable discovery API routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from thalos_prime.discovery import Claim, Constraint, DiscoveryEngine, Evidence, Observation

router = APIRouter()
ScalarInput = str | int | float | bool


class EvidenceInput(BaseModel):
    """Evidence item attached to a structured claim."""
    evidence_id: str
    statement: str
    source_uri: str | None = None
    evidence_kind: str = "unspecified"
    independently_checked: bool = False


class ClaimInput(BaseModel):
    """Structured claim with an optional canonical proposition key."""
    claim_id: str
    text: str
    domain: str = "unspecified"
    proposition_key: str | None = None
    polarity: bool = True
    assumptions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceInput] = Field(default_factory=list)


class ConstraintInput(BaseModel):
    """Declarative comparison with exactly one right-hand operand."""
    name: str
    left_variable: str
    operator: str
    right_value: ScalarInput | None = None
    right_variable: str | None = None
    explanation: str = ""

    @model_validator(mode="after")
    def check_operands(self) -> ConstraintInput:
        """Reject ambiguous or unsupported operands."""
        if (self.right_value is None) == (self.right_variable is None):
            raise ValueError("set exactly one of right_value or right_variable")
        if self.operator not in {"eq", "ne", "lt", "le", "gt", "ge"}:
            raise ValueError("operator must be eq, ne, lt, le, gt, or ge")
        return self


class ObservationInput(BaseModel):
    """Reported test result linked to a generated hypothesis ID."""
    observation_id: str
    hypothesis_id: str
    outcome: str
    method: str
    source_uri: str | None = None
    setup_hash: str | None = None
    reproducible: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def check_observation(self) -> ObservationInput:
        """Require reproducibility metadata when the submitter asserts reproducibility."""
        if self.reproducible and not self.setup_hash:
            raise ValueError("reproducible observations require a setup_hash")
        if self.outcome not in {"supports", "refutes", "inconclusive"}:
            raise ValueError("outcome must be supports, refutes, or inconclusive")
        return self


class DiscoveryRequest(BaseModel):
    """Validated input contract for discovery analysis."""
    question: str = Field(min_length=1, max_length=8000)
    claims: list[ClaimInput] = Field(default_factory=list)
    constraints: list[ConstraintInput] = Field(default_factory=list)
    values: dict[str, ScalarInput] | None = None
    observations: list[ObservationInput] = Field(default_factory=list)
    max_hypotheses: int = Field(default=5, ge=1, le=7)


@router.post("/analyze")
async def analyze_discovery(request: DiscoveryRequest) -> dict[str, Any]:
    """Return candidate hypotheses, conflicts, constraints and test plans."""
    try:
        claims = tuple(Claim(
            claim_id=item.claim_id, text=item.text, domain=item.domain,
            proposition_key=item.proposition_key, polarity=item.polarity,
            assumptions=tuple(item.assumptions),
            evidence=tuple(Evidence(**ev.model_dump()) for ev in item.evidence),
        ) for item in request.claims)
        constraints = tuple(Constraint(**item.model_dump()) for item in request.constraints)
        observations = tuple(Observation(**item.model_dump()) for item in request.observations)
        report = DiscoveryEngine().analyze(
            question=request.question, claims=claims, constraints=constraints,
            values=request.values, observations=observations,
            max_hypotheses=request.max_hypotheses,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return report.to_dict()
