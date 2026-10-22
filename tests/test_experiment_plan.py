"""Tests for the declarative research execution plan."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from thalos_prime.experiments.plan import (
    ExperimentPlan,
    StageSpec,
    default_research_plan,
)


def test_default_plan_is_dependency_ordered() -> None:
    plan = default_research_plan()
    assert plan.topological_order() == [
        "define_task",
        "ingest_evidence",
        "construct_representations",
        "generate_candidates",
        "run_validation",
        "compare_baseline",
        "persist_report",
    ]


def test_ready_stages_are_stable_and_only_include_unblocked_work() -> None:
    plan = ExperimentPlan(
        plan_id="parallel-plan",
        stages=[
            StageSpec(stage_id="z", operation="z"),
            StageSpec(stage_id="a", operation="a"),
            StageSpec(stage_id="join", operation="join", depends_on=["a", "z"]),
        ],
    )
    assert plan.ready_stages(set()) == ["a", "z"]
    assert plan.ready_stages({"a"}) == ["z"]
    assert plan.ready_stages({"a", "z"}) == ["join"]


def test_unknown_dependency_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown dependencies"):
        ExperimentPlan(
            plan_id="bad-dependency",
            stages=[
                StageSpec(stage_id="a", operation="a", depends_on=["missing"]),
            ],
        )


def test_cycles_are_rejected() -> None:
    with pytest.raises(ValidationError, match="stage dependency cycle detected"):
        ExperimentPlan(
            plan_id="cycle",
            stages=[
                StageSpec(stage_id="a", operation="a", depends_on=["b"]),
                StageSpec(stage_id="b", operation="b", depends_on=["a"]),
            ],
        )


def test_duplicate_stage_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="stage identifiers must be unique"):
        ExperimentPlan(
            plan_id="duplicate",
            stages=[
                StageSpec(stage_id="a", operation="first"),
                StageSpec(stage_id="a", operation="second"),
            ],
        )


def test_unknown_completed_stage_is_rejected() -> None:
    with pytest.raises(ValueError, match="contains unknown stages"):
        default_research_plan().ready_stages({"not-in-plan"})
