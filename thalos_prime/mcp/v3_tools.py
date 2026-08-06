"""MCP-facing adapters for the Thalos Prime epistemic v3 engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from thalos_prime.epistemic_v3.challenge import ChallengeEngine
from thalos_prime.epistemic_v3.claim_ir import ClaimCompiler, ClaimIR, ClaimType
from thalos_prime.epistemic_v3.counterfactual import CounterfactualEngine, CounterfactualReport
from thalos_prime.epistemic_v3.decision import DecisionArtifact, DecisionCompiler
from thalos_prime.epistemic_v3.lattice import BeliefLattice, BeliefPosition
from thalos_prime.epistemic_v3.stability import StabilityAnalyzer, StabilityReport
from thalos_prime.epistemic_v3.transaction import EpistemicTransaction
from thalos_prime.epistemic_v3.vm import DEFAULT_INVESTIGATION_PROGRAM, EpistemicVM
from thalos_prime.epistemic_v3.warrant import Warrant, WarrantAlgebra, WarrantOperation
from thalos_prime.epistemic_v3.witness import Witness, WitnessCalculus


@dataclass
class ThalosV3Runtime:
    """State-free computational adapter for the new epistemic substrate.

    It deliberately does not commit beliefs or mutate the authoritative event
    ledger. The existing transactional runtime remains responsible for durable
    state changes; this layer computes claims, challenges, warrant transforms,
    lattice positions, decision artifacts, stability reports,
    counterfactual sensitivity, and immutable transaction aggregates that can
    be fed into those writes.
    """

    vm: EpistemicVM = field(default_factory=EpistemicVM)
    lattice: BeliefLattice = field(default_factory=BeliefLattice)
    stability: StabilityAnalyzer = field(default_factory=StabilityAnalyzer)
    counterfactual: CounterfactualEngine = field(default_factory=CounterfactualEngine)
    decision: DecisionCompiler = field(default_factory=DecisionCompiler)

    def compile_claim(self, *, text: str, claim_type: str | None = None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if claim_type is not None:
            kwargs["claim_type"] = ClaimType(claim_type)
        result = ClaimCompiler.compile(text, **kwargs)
        return {"claim": result.claim.model_dump(mode="json"), "warnings": result.warnings}

    def build_challenge_plan(self, *, claim: dict[str, Any]) -> dict[str, Any]:
        compiled = ClaimIR.model_validate(claim)
        return ChallengeEngine.build_plan(compiled).model_dump(mode="json")

    def classify_belief(
        self,
        *,
        claim_id: str,
        warrant: dict[str, Any],
        challenge_count: int = 0,
        resolved_challenge_count: int = 0,
        failed_challenge_count: int = 0,
    ) -> dict[str, Any]:
        position = self.lattice.classify(
            claim_id=claim_id,
            warrant=Warrant.model_validate(warrant),
            challenge_count=challenge_count,
            resolved_challenge_count=resolved_challenge_count,
            failed_challenge_count=failed_challenge_count,
        )
        return position.model_dump(mode="json")

    def compile_decision(
        self,
        *,
        belief_position: dict[str, Any],
        stability_report: dict[str, Any],
        counterfactual_report: dict[str, Any],
    ) -> dict[str, Any]:
        artifact = self.decision.compile(
            belief=BeliefPosition.model_validate(belief_position),
            stability=StabilityReport.model_validate(stability_report),
            counterfactual=CounterfactualReport.model_validate(counterfactual_report),
        )
        return artifact.model_dump(mode="json")

    def run_program(self, *, query: str, warrant: dict[str, Any], challenge_count: int = 0) -> dict[str, Any]:
        result = self.vm.execute(
            DEFAULT_INVESTIGATION_PROGRAM,
            {
                "query": query,
                "warrant": Warrant.model_validate(warrant),
                "challenge_count": challenge_count,
                "resolved_challenge_count": 0,
                "failed_challenge_count": 0,
            },
        )
        return result.model_dump(mode="json")

    def analyze_witnesses(self, *, witnesses: list[dict[str, Any]], witness_ids: list[str]) -> dict[str, Any]:
        parsed = [Witness.model_validate(witness) for witness in witnesses]
        analysis = WitnessCalculus(parsed).analyze(witness_ids)
        return {
            "eligible_witness_ids": analysis.eligible_witness_ids,
            "independent_groups": analysis.independent_groups,
            "root_lineages": analysis.root_lineages,
            "independence_score": analysis.independence_score,
            "correlation_penalty": analysis.correlation_penalty,
        }

    def transform_warrant(
        self,
        *,
        operation: str,
        warrant: dict[str, Any] | None = None,
        warrants: list[dict[str, Any]] | None = None,
        parameter: float | None = None,
    ) -> dict[str, Any]:
        op = WarrantOperation(operation)
        if op is WarrantOperation.COPY:
            if warrant is None:
                raise ValueError("copy requires warrant")
            transfer = WarrantAlgebra.copy(Warrant.model_validate(warrant))
        elif op is WarrantOperation.PARAPHRASE:
            if warrant is None:
                raise ValueError("paraphrase requires warrant")
            transfer = WarrantAlgebra.paraphrase(Warrant.model_validate(warrant), parameter or 1.0)
        elif op is WarrantOperation.SUMMARIZE:
            if warrant is None:
                raise ValueError("summarize requires warrant")
            transfer = WarrantAlgebra.summarize(Warrant.model_validate(warrant), parameter or 1.0)
        elif op is WarrantOperation.DEDUCE:
            if not warrants:
                raise ValueError("deduce requires warrants")
            transfer = WarrantAlgebra.deduce([Warrant.model_validate(item) for item in warrants], parameter or 1.0)
        elif op is WarrantOperation.CORROBORATE:
            if not warrants:
                raise ValueError("corroborate requires warrants")
            transfer = WarrantAlgebra.corroborate([Warrant.model_validate(item) for item in warrants], parameter or 0.0)
        elif op is WarrantOperation.CONTRADICT:
            if warrant is None:
                raise ValueError("contradict requires warrant")
            transfer = WarrantAlgebra.contradict(Warrant.model_validate(warrant), parameter or 0.0)
        elif op is WarrantOperation.SPECULATE:
            if warrant is None:
                raise ValueError("speculate requires warrant")
            transfer = WarrantAlgebra.speculate(Warrant.model_validate(warrant))
        else:
            raise ValueError(f"unsupported warrant operation: {operation}")
        return {
            "operation": transfer.operation.value,
            "input_warrant": transfer.input_warrant.model_dump(mode="json"),
            "output_warrant": transfer.output_warrant.model_dump(mode="json"),
            "rule_id": transfer.rule_id,
            "explanation": transfer.explanation,
            "conserved": transfer.conserved,
        }

    def stability_report(
        self,
        *,
        evidence_ids: list[str],
        baseline_decision: str,
        decisions: dict[str, str],
    ) -> dict[str, Any]:
        def decide(ids: tuple[str, ...]) -> str:
            return decisions.get("|".join(ids), baseline_decision)

        report = self.stability.analyze(
            evidence_ids=evidence_ids,
            baseline_decision=baseline_decision,
            decide=decide,
            max_removals=1,
        )
        return report.model_dump(mode="json")

    def counterfactual_report(
        self,
        *,
        evidence_ids: list[str],
        baseline_decision: str,
        decisions: dict[str, str],
        max_removal_order: int = 2,
    ) -> dict[str, Any]:
        def decide(ids: tuple[str, ...]) -> str:
            return decisions.get("|".join(ids), baseline_decision)

        engine = CounterfactualEngine(max_removal_order=max_removal_order)
        report = engine.analyze(
            evidence_ids=evidence_ids,
            baseline_decision=baseline_decision,
            decide=decide,
        )
        return report.model_dump(mode="json")

    def build_transaction(
        self,
        *,
        claim: dict[str, Any],
        challenge_plan_id: str,
        witness_analysis: dict[str, Any],
        warrant: dict[str, Any],
        belief_position: dict[str, Any],
        decision_artifact: dict[str, Any],
        stability_report: dict[str, Any],
        counterfactual_report: dict[str, Any],
        source_snapshot_id: str | None = None,
        run_id: str | None = None,
        proof_bundle_id: str | None = None,
    ) -> dict[str, Any]:
        transaction = EpistemicTransaction.create(
            claim=ClaimIR.model_validate(claim),
            challenge_plan_id=challenge_plan_id,
            witness_analysis=witness_analysis,
            warrant=Warrant.model_validate(warrant),
            belief_position=BeliefPosition.model_validate(belief_position),
            decision_artifact=DecisionArtifact.model_validate(decision_artifact),
            stability_report=StabilityReport.model_validate(stability_report),
            counterfactual_report=CounterfactualReport.model_validate(counterfactual_report),
            source_snapshot_id=source_snapshot_id,
            run_id=run_id,
            proof_bundle_id=proof_bundle_id,
        )
        return transaction.model_dump(mode="json")


def register_v3_tools(mcp: Any, runtime: ThalosV3Runtime | None = None) -> ThalosV3Runtime:
    """Register v3 computational tools on an existing FastMCP server."""
    state = runtime or ThalosV3Runtime()
    mcp.tool(name="thalos.v3.claim.compile")(state.compile_claim)
    mcp.tool(name="thalos.v3.challenge.plan")(state.build_challenge_plan)
    mcp.tool(name="thalos.v3.belief.classify")(state.classify_belief)
    mcp.tool(name="thalos.v3.decision.compile")(state.compile_decision)
    mcp.tool(name="thalos.v3.program.run")(state.run_program)
    mcp.tool(name="thalos.v3.witness.analyze")(state.analyze_witnesses)
    mcp.tool(name="thalos.v3.warrant.transform")(state.transform_warrant)
    mcp.tool(name="thalos.v3.stability.analyze")(state.stability_report)
    mcp.tool(name="thalos.v3.counterfactual.analyze")(state.counterfactual_report)
    mcp.tool(name="thalos.v3.transaction.build")(state.build_transaction)
    return state
