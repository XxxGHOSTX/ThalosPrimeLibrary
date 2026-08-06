"""Tests for explicit Thalos Prime decision compilation."""

from __future__ import annotations

from thalos_prime.epistemic_v3.counterfactual import CounterfactualEngine
from thalos_prime.epistemic_v3.decision import DecisionCompiler, DecisionReason
from thalos_prime.epistemic_v3.lattice import BeliefLattice, DecisionState
from thalos_prime.epistemic_v3.stability import StabilityAnalyzer
from thalos_prime.epistemic_v3.warrant import Warrant


def _warrant(**overrides: float) -> Warrant:
    values = {
        "support": 0.95,
        "contradiction": 0.0,
        "entailment": 0.95,
        "temporal_validity": 1.0,
        "scope_validity": 0.95,
        "independence": 0.95,
        "provenance_integrity": 1.0,
        "reproducibility": 1.0,
        "falsifiability": 0.95,
    }
    values.update(overrides)
    return Warrant(**values)


def test_decision_compiler_downgrades_fragile_acceptance() -> None:
    belief = BeliefLattice().classify(
        claim_id="clmir:test",
        warrant=_warrant(),
        challenge_count=0,
        resolved_challenge_count=0,
        failed_challenge_count=0,
    )

    def decide(ids: tuple[str, ...]) -> str:
        return "accepted" if len(ids) >= 2 else "pending"

    stability = StabilityAnalyzer().analyze(
        evidence_ids=("a", "b"),
        baseline_decision="accepted",
        decide=decide,
        max_removals=1,
    )
    counterfactual = CounterfactualEngine(max_removal_order=1).analyze(
        evidence_ids=("a", "b"),
        baseline_decision="accepted",
        decide=decide,
    )
    artifact = DecisionCompiler().compile(
        belief=belief,
        stability=stability,
        counterfactual=counterfactual,
    )
    assert artifact.input_decision is DecisionState.ACCEPTED
    assert artifact.final_decision is DecisionState.PROVISIONAL
    assert DecisionReason.STABILITY_LOW in artifact.reasons
    assert DecisionReason.CRITICAL_EVIDENCE in artifact.reasons
    assert artifact.safe_to_state_as_fact is False


def test_decision_compiler_keeps_stable_redundant_acceptance() -> None:
    belief = BeliefLattice().classify(
        claim_id="clmir:test",
        warrant=_warrant(),
        challenge_count=0,
        resolved_challenge_count=0,
        failed_challenge_count=0,
    )

    def decide(ids: tuple[str, ...]) -> str:
        return "accepted"

    evidence = ("a", "b", "c")
    stability = StabilityAnalyzer().analyze(
        evidence_ids=evidence,
        baseline_decision="accepted",
        decide=decide,
        max_removals=1,
    )
    counterfactual = CounterfactualEngine(max_removal_order=1).analyze(
        evidence_ids=evidence,
        baseline_decision="accepted",
        decide=decide,
    )
    artifact = DecisionCompiler().compile(
        belief=belief,
        stability=stability,
        counterfactual=counterfactual,
    )
    assert artifact.final_decision is DecisionState.ACCEPTED
    assert artifact.safe_to_state_as_fact is True
    assert DecisionReason.STABLE_AND_REDUNDANT in artifact.reasons
