"""Declarative dependency graph for the ThalosPrime research workflow.

Plans describe which stages depend on others. They do not contain executable
callables; an execution service must resolve operation names through an
explicit registry and apply runtime, permission, and resource limits.
"""

from __future__ import annotations

import heapq

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StageSpec(BaseModel):
    """Metadata and dependencies for one named workflow stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    timeout_seconds: float = Field(default=60.0, gt=0, allow_inf_nan=False)
    requires_approval: bool = False

    @field_validator("stage_id", "operation")
    @classmethod
    def validate_names(cls, value: str) -> str:
        """Reject blank stage IDs and operation names."""
        value = value.strip()
        if not value:
            raise ValueError("stage identifiers and operation names must not be blank")
        return value

    @field_validator("depends_on")
    @classmethod
    def validate_dependencies(cls, values: list[str]) -> list[str]:
        """Reject empty and duplicate dependency names."""
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("dependency identifiers must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("stage dependencies must be unique")
        return normalized


class ExperimentPlan(BaseModel):
    """Validated directed acyclic graph for a research experiment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_id: str = Field(min_length=1)
    version: str = Field(default="1", min_length=1)
    stages: list[StageSpec] = Field(min_length=1)

    @field_validator("plan_id", "version")
    @classmethod
    def validate_identity(cls, value: str) -> str:
        """Reject blank plan IDs and versions."""
        value = value.strip()
        if not value:
            raise ValueError("plan identifiers and versions must not be blank")
        return value

    @model_validator(mode="after")
    def validate_graph(self) -> ExperimentPlan:
        """Require unique stages, known dependencies, and an acyclic graph."""
        ids = [stage.stage_id for stage in self.stages]
        if len(ids) != len(set(ids)):
            raise ValueError("stage identifiers must be unique")
        known = set(ids)
        for stage in self.stages:
            if stage.stage_id in stage.depends_on:
                raise ValueError(f"stage {stage.stage_id!r} cannot depend on itself")
            missing = sorted(set(stage.depends_on) - known)
            if missing:
                raise ValueError(
                    f"stage {stage.stage_id!r} references unknown dependencies: "
                    + ", ".join(missing)
                )
        _resolve_order(self.stages)
        return self

    def topological_order(self) -> list[str]:
        """Return a stable topological ordering of stage IDs."""
        return _resolve_order(self.stages)

    def ready_stages(self, completed_stage_ids: set[str]) -> list[str]:
        """Return stages whose dependencies are complete, in stable order.

        This is a scheduling helper, not an executor. It intentionally does
        not mark stages complete or run their operation handlers.
        """
        known = {stage.stage_id for stage in self.stages}
        unknown_completed = completed_stage_ids - known
        if unknown_completed:
            raise ValueError(
                "completed_stage_ids contains unknown stages: "
                + ", ".join(sorted(unknown_completed))
            )
        return [
            stage_id
            for stage_id in self.topological_order()
            if stage_id not in completed_stage_ids
            and set(next(stage for stage in self.stages if stage.stage_id == stage_id).depends_on)
            <= completed_stage_ids
        ]


def _resolve_order(stages: list[StageSpec]) -> list[str]:
    """Resolve a deterministic topological order or reject a dependency cycle."""
    dependencies = {stage.stage_id: set(stage.depends_on) for stage in stages}
    dependents: dict[str, list[str]] = {stage.stage_id: [] for stage in stages}
    for stage_id, stage_dependencies in dependencies.items():
        for dependency in stage_dependencies:
            dependents[dependency].append(stage_id)
    for children in dependents.values():
        children.sort()
    ready = [stage_id for stage_id, deps in dependencies.items() if not deps]
    heapq.heapify(ready)
    order: list[str] = []
    remaining = {stage_id: set(deps) for stage_id, deps in dependencies.items()}
    while ready:
        stage_id = heapq.heappop(ready)
        order.append(stage_id)
        for child in dependents[stage_id]:
            remaining[child].discard(stage_id)
            if not remaining[child]:
                heapq.heappush(ready, child)
    if len(order) != len(stages):
        cyclic = sorted(set(dependencies) - set(order))
        raise ValueError("stage dependency cycle detected: " + ", ".join(cyclic))
    return order


def default_research_plan(plan_id: str = "thalos-research-v1") -> ExperimentPlan:
    """Return the canonical declarative research workflow.

    Operation names are identifiers only. A runtime must provide explicitly
    registered handlers before any stage can be executed.
    """
    return ExperimentPlan(
        plan_id=plan_id,
        version="1",
        stages=[
            StageSpec(stage_id="define_task", operation="define_task"),
            StageSpec(
                stage_id="ingest_evidence",
                operation="ingest_evidence",
                depends_on=["define_task"],
            ),
            StageSpec(
                stage_id="construct_representations",
                operation="construct_representations",
                depends_on=["ingest_evidence"],
            ),
            StageSpec(
                stage_id="generate_candidates",
                operation="generate_candidates",
                depends_on=["construct_representations"],
            ),
            StageSpec(
                stage_id="run_validation",
                operation="run_validation",
                depends_on=["generate_candidates"],
            ),
            StageSpec(
                stage_id="compare_baseline",
                operation="compare_baseline",
                depends_on=["run_validation"],
            ),
            StageSpec(
                stage_id="persist_report",
                operation="persist_report",
                depends_on=["compare_baseline"],
            ),
        ],
    )


__all__ = ["ExperimentPlan", "StageSpec", "default_research_plan"]
