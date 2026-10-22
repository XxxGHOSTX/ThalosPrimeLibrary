"""API endpoints for declarative experiment planning and result comparison.

These endpoints operate on recorded measurements. They do not execute model
outputs, generated code, shell commands, or candidate implementations.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from thalos_prime.experiments.contracts import CandidateRun, ExperimentSpec
from thalos_prime.experiments.evaluator import ExperimentEvaluator
from thalos_prime.experiments.plan import default_research_plan

router = APIRouter()


class CompareExperimentRequest(BaseModel):
    """Request body for comparing candidate results with a baseline."""

    model_config = ConfigDict(extra="forbid")

    spec: ExperimentSpec
    runs: list[CandidateRun]


@router.get("/plan/default")
async def get_default_plan() -> dict[str, Any]:
    """Return the validated default declarative workflow plan."""
    return default_research_plan().model_dump(mode="json")


@router.post("/compare")
async def compare_experiment(request: CompareExperimentRequest) -> dict[str, Any]:
    """Compare supplied measurements against a named baseline."""
    try:
        report = ExperimentEvaluator.compare(request.spec, request.runs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return report.model_dump(mode="json")


__all__ = ["router"]
