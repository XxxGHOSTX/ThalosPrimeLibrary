"""Tests for immutable epistemic transaction aggregation."""

from __future__ import annotations

from thalos_prime.epistemic_v3.challenge import ChallengeEngine
from thalos_prime.epistemic_v3.claim_ir import ClaimCompiler
from thalos_prime.epistemic_v3.counterfactual import CounterfactualEngine
from thalos_prime.epistemic_v3.lattice import BeliefLattice
from thalos_prime.epistemic_v3.stability import StabilityAnalyzer
from thalos_prime.epistemic_v3.transaction import EpistemicTransaction
from thalos_prime.epistemic_v3.warrant import Warrant
from thalos_prime.epistemic_v3.witness import Witness, WitnessCalculus, WitnessKind


def test_transaction_fingerprint_is_content_addressed() -> None:
    claim = ClaimCompiler.compile("Revenue increased in 2025.").claim
    plan = ChallengeEngine.build_plan(claim)
    witness = Witness.create("src:1", WitnessKind.RECORD, issuer="A")
    witness_analysis = WitnessCalculus([witness]).analyze([witness.witness_id])
    warrant = Warrant(
        support=0.9,
        contradiction=0.0,
        entailment=0.9,
        temporal_validity=1.0,
        scope_validity=0.9,
        independence=1.0,
        provenance_integrity=1.0,
        reproducibility=1.0,
        falsifiability=1.0,
    )
    lattice = BeliefLattice()
    belief = lattice.classify(
        claim_id=claim.claim_id,
        warrant=warrant,
        challenge_count=0,
        resolved_challenge_count=0,
        failed_challenge_count=0,
    )

    def decide(ids: tuple[str, ...]) -> str:
        return belief.decision.value

    stability = StabilityAnalyzer().analyze(
        evidence_ids=(witness.witness_id,),
        baseline_decision=belief.decision.value,
        decide=decide,
        max_removals=1,
    )
    counterfactual = CounterfactualEngine(max_removal_order=1).analyze(
        evidence_ids=(witness.witness_id,),
        baseline_decision=belief.decision.value,
        decide=decide,
    )
    first = EpistemicTransaction.create(
        claim=claim,
        challenge_plan_id=plan.plan_id,
        witness_analysis=witness_analysis,
        warrant=warrant,
        belief_position=belief,
        stability_report=stability,
        counterfactual_report=counterfactual,
    )
    second = EpistemicTransaction.create(
        claim=claim,
        challenge_plan_id=plan.plan_id,
        witness_analysis=witness_analysis,
        warrant=warrant,
        belief_position=belief,
        stability_report=stability,
        counterfactual_report=counterfactual,
    )
    assert first.transaction_id == second.transaction_id
    assert first.fingerprint == second.fingerprint
    assert first.ready_for_commit is True


def test_transaction_commit_binding_changes_only_commit_reference() -> None:
    claim = ClaimCompiler.compile("Revenue increased.").claim
    plan = ChallengeEngine.build_plan(claim)
    warrant = Warrant(
        support=0.6,
        contradiction=0.0,
        entailment=0.7,
        temporal_validity=1.0,
        scope_validity=0.8,
        independence=0.7,
        provenance_integrity=1.0,
        reproducibility=1.0,
        falsifiability=0.8,
    )
    belief = BeliefLattice().classify(
        claim_id=claim.claim_id,
        warrant=warrant,
        challenge_count=1,
        resolved_challenge_count=0,
        failed_challenge_count=0,
    )
    stability = StabilityAnalyzer().analyze(
        evidence_ids=(),
        baseline_decision=belief.decision.value,
        decide=lambda _: belief.decision.value,
        max_removals=1,
    )
    counterfactual = CounterfactualEngine().analyze(
        evidence_ids=(),
        baseline_decision=belief.decision.value,
        decide=lambda _: belief.decision.value,
    )
    txn = EpistemicTransaction.create(
        claim=claim,
        challenge_plan_id=plan.plan_id,
        witness_analysis={},
        warrant=warrant,
        belief_position=belief,
        stability_report=stability,
        counterfactual_report=counterfactual,
    )
    bound = txn.bind_commit("evt:123")
    assert txn.transaction_id == bound.transaction_id
    assert txn.fingerprint == bound.fingerprint
    assert bound.committed_event_id == "evt:123"
