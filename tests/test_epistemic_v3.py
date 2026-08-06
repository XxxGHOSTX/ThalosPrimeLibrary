"""Tests for the Thalos Prime epistemic computing v3 layer."""

from __future__ import annotations

from thalos_prime.epistemic_v3.challenge import ChallengeEngine, ChallengeKind
from thalos_prime.epistemic_v3.claim_ir import ClaimCompiler, ClaimType
from thalos_prime.epistemic_v3.lattice import BeliefLattice, DecisionState, StabilityState
from thalos_prime.epistemic_v3.stability import StabilityAnalyzer
from thalos_prime.epistemic_v3.vm import DEFAULT_INVESTIGATION_PROGRAM, EpistemicVM
from thalos_prime.epistemic_v3.warrant import Warrant, WarrantAlgebra
from thalos_prime.epistemic_v3.witness import Witness, WitnessCalculus, WitnessKind


def _warrant(**overrides: float) -> Warrant:
    values = {
        "support": 0.9,
        "contradiction": 0.0,
        "entailment": 0.95,
        "temporal_validity": 1.0,
        "scope_validity": 0.95,
        "independence": 0.9,
        "provenance_integrity": 1.0,
        "reproducibility": 1.0,
        "falsifiability": 0.9,
    }
    values.update(overrides)
    return Warrant(**values)


def test_claim_compiler_produces_stable_identity_and_temporal_scope() -> None:
    first = ClaimCompiler.compile("Revenue increased in 2025.")
    second = ClaimCompiler.compile("Revenue increased in 2025.")
    assert first.claim.claim_id == second.claim.claim_id
    assert first.claim.claim_type is ClaimType.TEMPORAL
    assert first.claim.valid_from == "2025"
    assert first.claim.valid_to == "2025"
    assert any("semantic slots" in warning for warning in first.warnings)


def test_claim_compiler_does_not_invent_semantic_slots() -> None:
    result = ClaimCompiler.compile("The bridge caused traffic to increase.")
    assert result.claim.claim_type is ClaimType.CAUSAL
    assert result.claim.subject is None
    assert result.claim.predicate is None
    assert result.claim.object is None


def test_witness_calculus_detects_derived_source_correlation() -> None:
    root = Witness.create("src:root", WitnessKind.RECORD, issuer="A")
    derived_a = Witness.create("src:a", WitnessKind.DERIVED, issuer="B", parent_witness_ids=[root.witness_id])
    derived_b = Witness.create("src:b", WitnessKind.DERIVED, issuer="C", parent_witness_ids=[root.witness_id])
    independent = Witness.create("src:d", WitnessKind.MEASUREMENT, issuer="D")
    analysis = WitnessCalculus([root, derived_a, derived_b, independent]).analyze(
        [derived_a.witness_id, derived_b.witness_id, independent.witness_id]
    )
    assert len(analysis.root_lineages) == 2
    assert analysis.correlation_penalty > 0.0
    assert len(analysis.independent_groups) == 2


def test_witness_calculus_rejects_genealogy_cycles() -> None:
    first = Witness(
        witness_id="wit:first",
        artifact_id="src:first",
        kind=WitnessKind.DERIVED,
        parent_witness_ids=("wit:second",),
    )
    second = Witness(
        witness_id="wit:second",
        artifact_id="src:second",
        kind=WitnessKind.DERIVED,
        parent_witness_ids=("wit:first",),
    )
    try:
        WitnessCalculus([first, second])
    except ValueError as exc:
        assert "cycle" in str(exc).lower()
    else:
        raise AssertionError("Expected cyclic witness genealogy to be rejected")


def test_warrant_algebra_preserves_or_explicitly_accounts_for_warrant_transfer() -> None:
    base = _warrant()
    paraphrase = WarrantAlgebra.paraphrase(base, fidelity=0.8)
    assert paraphrase.output_warrant.usable_support <= base.usable_support
    assert paraphrase.conserved

    speculative = WarrantAlgebra.speculate(base)
    assert speculative.output_warrant.support == 0.0
    assert speculative.conserved

    corroborated = WarrantAlgebra.corroborate([base, _warrant(support=0.7)], independence=1.0)
    assert corroborated.output_warrant.support >= base.support
    assert corroborated.operation.value == "corroborate"
    assert corroborated.rule_id == "warrant.corroborate.v1"


def test_challenge_engine_generates_causal_falsification_shadow() -> None:
    claim = ClaimCompiler.compile("Policy X caused unemployment to fall.").claim
    plan = ChallengeEngine.build_plan(claim)
    kinds = {task.kind for task in plan.tasks}
    assert ChallengeKind.COUNTEREVIDENCE in kinds
    assert ChallengeKind.CAUSAL in kinds
    assert ChallengeKind.ALTERNATIVE_EXPLANATION in kinds
    assert plan.required_task_count >= 6


def test_belief_lattice_keeps_contradiction_visible() -> None:
    lattice = BeliefLattice()
    position = lattice.classify(
        claim_id="clmir:test",
        warrant=_warrant(contradiction=0.8),
        challenge_count=4,
        resolved_challenge_count=2,
        failed_challenge_count=0,
    )
    assert position.decision is DecisionState.DISPUTED
    assert position.information_state.value == "both"
    assert position.unresolved_challenges == 2
    assert position.stability in {StabilityState.STABLE, StabilityState.MODERATE}


def test_epistemic_vm_is_replayable_for_same_inputs() -> None:
    vm = EpistemicVM()
    inputs = {
        "query": "Revenue increased in 2025.",
        "warrant": _warrant(),
        "challenge_count": 0,
        "resolved_challenge_count": 0,
        "failed_challenge_count": 0,
    }
    first = vm.execute(DEFAULT_INVESTIGATION_PROGRAM, inputs)
    second = vm.execute(DEFAULT_INVESTIGATION_PROGRAM, inputs)
    assert first.execution_fingerprint == second.execution_fingerprint
    assert first.claim is not None
    assert first.challenge_plan_id is not None
    assert first.belief is not None
    assert first.belief.decision is DecisionState.ACCEPTED


def test_stability_analyzer_detects_fragile_decision() -> None:
    analyzer = StabilityAnalyzer()

    def decide(ids: tuple[str, ...]) -> str:
        return "accepted" if len(ids) >= 2 else "pending"

    report = analyzer.analyze(
        evidence_ids=("ev:a", "ev:b"),
        baseline_decision="accepted",
        decide=decide,
        max_removals=1,
    )
    assert report.perturbation_count == 3
    assert report.changed_decision_count == 2
    assert report.stability_score < 0.5
    assert report.reversibility_score > 0.5


def test_stability_analyzer_is_order_invariant_for_reordering() -> None:
    analyzer = StabilityAnalyzer()

    def decide(ids: tuple[str, ...]) -> str:
        return "accepted" if set(ids) == {"a", "b"} else "pending"

    report = analyzer.analyze(
        evidence_ids=("a", "b"),
        baseline_decision="accepted",
        decide=decide,
        max_removals=0,
    )
    assert report.perturbation_count == 1
    assert report.changed_decision_count == 0
    assert report.stability_score == 1.0
