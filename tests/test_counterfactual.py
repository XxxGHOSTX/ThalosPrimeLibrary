"""Tests for counterfactual evidence analysis."""

from __future__ import annotations

from thalos_prime.epistemic_v3.counterfactual import CounterfactualEngine


def test_counterfactual_engine_finds_minimal_flip() -> None:
    engine = CounterfactualEngine(max_removal_order=2)

    def decide(ids: tuple[str, ...]) -> str:
        return "accepted" if {"a", "b"}.issubset(ids) else "pending"

    report = engine.analyze(
        evidence_ids=("a", "b", "c"),
        baseline_decision="accepted",
        decide=decide,
    )
    assert report.cases_examined == 6
    assert report.minimal_flip_cases
    assert ("a",) in {case.removed_evidence for case in report.minimal_flip_cases}
    assert ("b",) in {case.removed_evidence for case in report.minimal_flip_cases}
    assert "a" in report.critical_evidence
    assert "b" in report.critical_evidence
    assert "c" not in report.critical_evidence
    assert "c" in report.robust_evidence


def test_counterfactual_engine_reports_no_flip_for_redundant_evidence() -> None:
    engine = CounterfactualEngine(max_removal_order=1)

    def decide(ids: tuple[str, ...]) -> str:
        return "accepted" if len(ids) >= 2 else "pending"

    report = engine.analyze(
        evidence_ids=("a", "b", "c"),
        baseline_decision="accepted",
        decide=decide,
    )
    assert report.flip_cases == ()
    assert report.minimal_flip_cases == ()
    assert report.critical_evidence == ()
    assert report.robust_evidence == ("a", "b", "c")
