"""Tests for the falsifiable discovery engine."""

from __future__ import annotations

import pytest

from thalos_prime.discovery import (
    Claim, Constraint, ConstraintStatus, DiscoveryEngine, HypothesisStatus, Observation,
)


def test_bottleneck_pattern_emits_prediction_and_falsifier() -> None:
    report = DiscoveryEngine().analyze("The throughput is slow due to a capacity bottleneck")
    assert report.hypotheses
    candidate = report.hypotheses[0]
    assert candidate.pattern_id == "capacity_bottleneck"
    assert candidate.status == HypothesisStatus.CANDIDATE
    assert "should" in candidate.prediction
    assert "show" in candidate.falsifier.lower()
    assert candidate.test_plan


def test_contradictions_require_canonical_key_and_inverse_polarity() -> None:
    claims = (
        Claim("a", "Stage is overloaded", proposition_key="stage-overloaded", polarity=True),
        Claim("b", "Stage is not overloaded", proposition_key="stage-overloaded", polarity=False),
        Claim("c", "Different unkeyed statement"),
    )
    report = DiscoveryEngine().analyze("capacity bottleneck", claims=claims)
    assert len(report.contradictions) == 1
    pair = report.contradictions[0]
    assert {pair["claim_a"], pair["claim_b"]} == {"a", "b"}


def test_constraints_report_satisfied_violated_and_unknown() -> None:
    constraints = (
        Constraint("minimum", "throughput", "ge", right_value=10),
        Constraint("available", "capacity", "ge", right_value=5),
        Constraint("missing", "unmeasured", "eq", right_value=1),
    )
    results = DiscoveryEngine().analyze(
        "capacity planning", constraints=constraints,
        values={"throughput": 12, "capacity": 3},
    ).constraint_results
    assert [item.status for item in results] == [
        ConstraintStatus.SATISFIED, ConstraintStatus.VIOLATED, ConstraintStatus.UNKNOWN
    ]


def test_observation_changes_status_without_claiming_independent_proof() -> None:
    first = DiscoveryEngine().analyze("capacity bottleneck").hypotheses[0]
    observation = Observation(
        "obs-1", first.hypothesis_id, "supports", "controlled throughput test",
        setup_hash="sha256:example", reproducible=True,
    )
    report = DiscoveryEngine().analyze("capacity bottleneck", observations=(observation,))
    assert report.hypotheses[0].status == HypothesisStatus.SUPPORTED
    assert any("not independently" in limit for limit in report.limitations)


def test_conflicting_observations_mark_hypothesis_contested() -> None:
    first = DiscoveryEngine().analyze("capacity bottleneck").hypotheses[0]
    observations = (
        Observation("support", first.hypothesis_id, "supports", "test A"),
        Observation("refute", first.hypothesis_id, "refutes", "test B"),
    )
    report = DiscoveryEngine().analyze("capacity bottleneck", observations=observations)
    assert report.hypotheses[0].status == HypothesisStatus.CONTESTED


def test_report_is_deterministic_and_values_affect_report_identity() -> None:
    engine = DiscoveryEngine()
    one = engine.analyze("threshold in system", values={"threshold": 5})
    two = engine.analyze("threshold in system", values={"threshold": 5})
    three = engine.analyze("threshold in system", values={"threshold": 6})
    assert one.to_dict() == two.to_dict()
    assert one.report_id != three.report_id
    assert one.hypotheses[0].hypothesis_id == three.hypotheses[0].hypothesis_id


def test_invalid_constraint_operator_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported operator"):
        Constraint("bad", "x", "exec", right_value=1)


def test_reproducible_observation_requires_setup_hash() -> None:
    with pytest.raises(ValueError, match="setup_hash"):
        Observation("o", "h", "supports", "test method", reproducible=True)


def test_no_matching_pattern_states_that_limitation() -> None:
    report = DiscoveryEngine().analyze("Describe a purple mountain in a poem")
    assert not report.hypotheses
    assert any("No library pattern matched" in item for item in report.missing_information)


def test_report_preserves_complete_observation_provenance() -> None:
    first = DiscoveryEngine().analyze("capacity bottleneck").hypotheses[0]
    observation = Observation(
        "source-observation", first.hypothesis_id, "supports", "bench protocol v2",
        source_uri="https://example.org/results", setup_hash="sha256:123",
        reproducible=True, notes="Raw run log attached",
    )
    payload = DiscoveryEngine().analyze(
        "capacity bottleneck", observations=(observation,),
    ).to_dict()
    record = payload["observations"][0]
    assert record["source_uri"] == "https://example.org/results"
    assert record["method"] == "bench protocol v2"
    assert record["setup_hash"] == "sha256:123"
    assert record["notes"] == "Raw run log attached"


def test_nonfinite_numeric_constraints_and_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="finite"):
        Constraint("bad-nan", "x", "eq", right_value=float("nan"))
    with pytest.raises(ValueError, match="finite"):
        DiscoveryEngine().analyze("capacity bottleneck", values={"throughput": float("inf")})


def test_non_string_question_is_rejected_cleanly() -> None:
    with pytest.raises(ValueError, match="question must be a string"):
        DiscoveryEngine().analyze(None)  # type: ignore[arg-type]
