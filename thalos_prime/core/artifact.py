"""Canonical artifact schema produced by the Thalos engine."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ArtifactCandidate(BaseModel):
    """Candidate solution emitted by the canonical pipeline."""

    candidate_id: str
    address: str
    text: str
    source: str
    coherence_score: float = Field(ge=0.0, le=100.0)
    constraint_score: float = Field(ge=0.0, le=100.0)
    purity_score: float = Field(ge=0.0, le=100.0)
    score: float = Field(ge=0.0, le=100.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    """Canonical output of ``ThalosEngine.run``."""

    input: str
    intent: dict[str, Any]
    research: dict[str, Any]
    constraints: dict[str, Any]
    candidates: list[ArtifactCandidate]
    selected: ArtifactCandidate
    plan: list[dict[str, Any]]
    seed: int
    version: str
    purity_metrics: dict[str, float]
    provenance_trace: list[dict[str, Any]]
    stabilization: dict[str, Any]
