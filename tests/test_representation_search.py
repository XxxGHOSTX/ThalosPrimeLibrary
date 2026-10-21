"""Tests for adaptive representation selection and infeasibility diagnosis."""

from __future__ import annotations

from thalos_prime.discovery import (
    AdaptiveRepresentationEngine,
    FiniteDomainProblem,
    RelationConstraint,
    VariableDomain,
)


def test_solver_agreement_and_witness_verification() -> None:
    problem = FiniteDomainProblem(
        "two-colors",
        (VariableDomain("left", (0, 1)), VariableDomain("right", (0, 1))),
        (RelationConstraint("different", "left", "ne", right_variable="right"),),
    )
    report = AdaptiveRepresentationEngine().solve(problem)
    assert report.verified is True
    assert report.verification_status == "witness_verified"
    assert {run.satisfiable for run in report.comparison_runs} == {True}
    assignment = dict(report.selected_result.solution or ())
    assert assignment["left"] != assignment["right"]


def test_mrv_finds_empty_legal_domain_before_exploring_unrelated_combinations() -> None:
    variables = tuple(VariableDomain(f"A{index}", (0, 1)) for index in range(8)) + (
        VariableDomain("Z", tuple(range(20))),
    )
    problem = FiniteDomainProblem(
        "late-contradiction",
        variables,
        (RelationConstraint("z-must-be-999", "Z", "eq", right_value=999),),
    )
    report = AdaptiveRepresentationEngine().solve(problem)
    runs = {run.strategy: run for run in report.comparison_runs}
    assert report.selected_strategy == "mrv"
    assert report.verification_status == "finite_domain_unsatisfiable"
    assert report.verified is True
    assert report.conflict_core == ("z-must-be-999",)
    assert report.repair_candidates[0]["constraint"] == "z-must-be-999"
    assert runs["mrv"].nodes_expanded < runs["fixed_order"].nodes_expanded
    assert runs["mrv"].nodes_expanded < runs["enumeration"].assignments_checked


def test_conflict_core_does_not_report_unrelated_constraint() -> None:
    problem = FiniteDomainProblem(
        "two-requirements",
        (VariableDomain("x", (0, 1)), VariableDomain("y", (0, 1))),
        (
            RelationConstraint("impossible-x", "x", "eq", right_value=9),
            RelationConstraint("valid-y", "y", "eq", right_value=1),
        ),
    )
    report = AdaptiveRepresentationEngine().solve(problem)
    assert report.conflict_core == ("impossible-x",)
    assert [item["constraint"] for item in report.repair_candidates] == ["impossible-x"]


def test_unknown_variables_and_duplicate_constraint_names_are_rejected() -> None:
    invalid_reference = (
        RelationConstraint("bad-ref", "y", "eq", right_value=1),
    )
    try:
        FiniteDomainProblem(
            "bad", (VariableDomain("x", (0, 1)),), invalid_reference,
        )
    except ValueError as exc:
        assert "undeclared variable" in str(exc)
    else:
        raise AssertionError("undeclared variable was accepted")

    duplicate_names = (
        RelationConstraint("same", "x", "eq", right_value=0),
        RelationConstraint("same", "x", "eq", right_value=1),
    )
    try:
        FiniteDomainProblem(
            "dupe", (VariableDomain("x", (0, 1)),), duplicate_names,
        )
    except ValueError as exc:
        assert "must be unique" in str(exc)
    else:
        raise AssertionError("duplicate constraint names were accepted")
