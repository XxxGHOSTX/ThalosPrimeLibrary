"""Tests for the declarative research execution plan."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from thalos_prime.experiments.plan import (
    ExperimentPlan,
    StageSpec,
    default_research_plan,
)


def test_default_plan_is_a_validated_multi_representation_dag() -> None:
    plan = default_research_plan()
    order = plan.topological_order()
    assert order[0] == "define_task"
    assert order[-1] == "persist_report"
    assert len(order) == 12
    positions = {stage_id: index for index, stage_id in enumerate(order)}
    assert positions["build_problem_model"] < positions["represent_graph"]
    assert positions["build_problem_model"] < positions["represent_constraints"]
    assert positions["build_problem_model"] < positions["represent_state_transition"]
    assert positions["represent_graph"] < positions["generate_graph_candidate"]
    assert positions["represent_constraints"] < positions["generate_constraint_candidate"]
    assert positions["represent_state_transition"] < positions["generate_state_candidate"]
    assert max(
        positions["generate_graph_candidate"],
        positions["generate_constraint_candidate"],
        positions["generate_state_candidate"],
    ) < positions["run_validation"]


def test_independent_representation_branches_can_be_ready_together() -> None:
    plan = default_research_plan()
    completed = {"define_task", "ingest_evidence", "build_problem_model"}
    assert plan.ready_stages(completed) == [
        "represent_constraints",
        "represent_graph",
        "represent_state_transition",
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
