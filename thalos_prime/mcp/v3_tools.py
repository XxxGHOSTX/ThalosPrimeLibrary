"""MCP-facing adapters for the Thalos Prime epistemic v3 engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from thalos_prime.epistemic_v3.challenge import ChallengeEngine
from thalos_prime.epistemic_v3.claim_ir import ClaimCompiler
from thalos_prime.epistemic_v3.lattice import BeliefLattice
from thalos_prime.epistemic_v3.stability import StabilityAnalyzer
from thalos_prime.epistemic_v3.vm import DEFAULT_INVESTIGATION_PROGRAM, EpistemicVM
from thalos_prime.epistemic_v3.warrant import Warrant, WarrantAlgebra
from thalos_prime.epistemic_v3.witness import Witness, WitnessCalculus, WitnessKind


@dataclass
class ThalosV3Runtime:
    """State-free computational adapter for the new epistemic substrate.

    It deliberately does not commit beliefs or mutate the authoritative event
    ledger. The existing transactional runtime remains responsible for durable
    state changes; this layer computes claims, challenges, warrant transforms,
    lattice positions, and stability reports that can be fed into those writes.
    """

    vm: EpistemicVM = field(default_factory=EpistemicVM)
    lattice: BeliefLattice = field(default_factory=BeliefLattice)
    stability: StabilityAnalyzer = field(default_factory=StabilityAnalyzer)

    def compile_claim(self, *, text: str, claim_type: str | None = None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if claim_type is not None:
            from thalos_prime.epistemic_v3.claim_ir import ClaimType

            kwargs["claim_type"] = ClaimType(claim_type)
        result = ClaimCompiler.compile(text, **kwargs)
        return {
            "claim": result.claim.model_dump(mode="json"),
            "warnings": result.warnings,
        }

    def build_challenge_plan(self, *, claim: dict[str, Any]) -> dict[str, Any]:
        from thalos_prime.epistemic_v3.claim_ir import ClaimIR

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
        return WitnessCalculus(parsed).analyze(witness_ids).to_dict() if hasattr(WitnessCalculus(parsed).analyze(witness_ids), "to_dict") else _witness_analysis_dict(WitnessCalculus(parsed).analyze(witness_ids))

    def transform_warrant(
        self,
        *,
        operation: str,
        warrant: dict[str, Any] | None = None,
        warrants: list[dict[str, Any]] | None = None,
        parameter: float | None = None,
    ) -> dict[str, Any]:
        from thalos_prime.epistemic_v3.warrant import WarrantOperation

        op = WarrantOperation(operation)
        if op.value == "copy":
            if warrant is None:
                raise ValueError("copy requires warrant")
            transfer = WarrantAlgebra.copy(Warrant.model_validate(warrant))
        elif op.value == "paraphrase":
            if warrant is None:
                raise ValueError("paraphrase requires warrant")
            transfer = WarrantAlgebra.paraphrase(Warrant.model_validate(warrant), parameter or 1.0)
        elif op.value == "summarize":
            if warrant is None:
                raise ValueError("summarize requires warrant")
            transfer = WarrantAlgebra.summarize(Warrant.model_validate(warrant), parameter or 1.0)
        elif op.value == "deduce":
            if not warrants:
                raise ValueError("deduce requires warrants")
            transfer = WarrantAlgebra.deduce([Warrant.model_validate(item) for item in warrants], parameter or 1.0)
        elif op.value == "corroborate":
            if not warrants:
                raise ValueError("corroborate requires warrants")
            transfer = WarrantAlgebra.corroborate([Warrant.model_validate(item) for item in warrants], parameter or 0.0)
        elif op.value == "contradict":
            if warrant is None:
                raise ValueError("contradict requires warrant")
            transfer = WarrantAlgebra.contradict(Warrant.model_validate(warrant), parameter or 0.0)
        elif op.value == "speculate":
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
            key = "|".join(ids)
            return decisions.get(key, baseline_decision)

        report = self.stability.analyze(
            evidence_ids=evidence_ids,
            baseline_decision=baseline_decision,
            decide=decide,
            max_removals=1,
        )
        return report.model_dump(mode="json")


def _witness_analysis_dict(analysis: Any) -> dict[str, Any]:
    return {
        "eligible_witness_ids": analysis.eligible_witness_ids,
        "independent_groups": analysis.independent_groups,
        "root_lineages": analysis.root_lineages,
        "independence_score": analysis.independence_score,
        "correlation_penalty": analysis.correlation_penalty,
    }


def register_v3_tools(mcp: Any, runtime: ThalosV3Runtime | None = None) -> ThalosV3Runtime:
    """Register v3 computational tools on an existing FastMCP server."""
    state = runtime or ThalosV3Runtime()
    mcp.tool(name="thalos.v3.claim.compile")(state.compile_claim)
    mcp.tool(name="thalos.v3.challenge.plan")(state.build_challenge_plan)
    mcp.tool(name="thalos.v3.belief.classify")(state.classify_belief)
    mcp.tool(name="thalos.v3.program.run")(state.run_program)
    mcp.tool(name="thalos.v3.witness.analyze")(state.analyze_witnesses)
    mcp.tool(name="thalos.v3.warrant.transform")(state.transform_warrant)
    mcp.tool(name="thalos.v3.stability.analyze")(state.stability_report)
    return state
