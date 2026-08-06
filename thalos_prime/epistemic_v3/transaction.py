"""Immutable epistemic transaction aggregate for Thalos Prime v3.

The transaction is the unit that binds the complete computational state of an
investigation before any durable belief commit occurs. It is intentionally
model-provider and MCP independent.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict

from thalos_prime.epistemic_v3.claim_ir import ClaimIR
from thalos_prime.epistemic_v3.counterfactual import CounterfactualReport
from thalos_prime.epistemic_v3.decision import DecisionArtifact
from thalos_prime.epistemic_v3.lattice import BeliefPosition, DecisionState
from thalos_prime.epistemic_v3.stability import StabilityReport
from thalos_prime.epistemic_v3.warrant import Warrant
from thalos_prime.epistemic_v3.witness import WitnessAnalysis


class EpistemicTransaction(BaseModel):
    """Content-addressed aggregate representing one complete epistemic computation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction_id: str
    claim: ClaimIR
    challenge_plan_id: str
    witness_analysis: Mapping[str, Any]
    warrant: Warrant
    belief_position: BeliefPosition
    decision_artifact: DecisionArtifact
    stability_report: StabilityReport
    counterfactual_report: CounterfactualReport
    source_snapshot_id: str | None = None
    run_id: str | None = None
    proof_bundle_id: str | None = None
    compiler_version: str = "epistemic-transaction-v2"
    committed_event_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        claim: ClaimIR,
        challenge_plan_id: str,
        witness_analysis: WitnessAnalysis | Mapping[str, Any],
        warrant: Warrant,
        belief_position: BeliefPosition,
        decision_artifact: DecisionArtifact,
        stability_report: StabilityReport,
        counterfactual_report: CounterfactualReport,
        source_snapshot_id: str | None = None,
        run_id: str | None = None,
        proof_bundle_id: str | None = None,
    ) -> "EpistemicTransaction":
        if decision_artifact.claim_id != claim.claim_id:
            raise ValueError("decision artifact does not belong to claim")
        if decision_artifact.input_decision is not belief_position.decision:
            raise ValueError("decision artifact input decision does not match belief position")
        if stability_report.baseline_decision != belief_position.decision.value:
            raise ValueError("stability baseline does not match belief position decision")
        if counterfactual_report.baseline_decision != belief_position.decision.value:
            raise ValueError("counterfactual baseline does not match belief position decision")

        if isinstance(witness_analysis, WitnessAnalysis):
            witness_payload: Mapping[str, Any] = {
                "eligible_witness_ids": witness_analysis.eligible_witness_ids,
                "independent_groups": witness_analysis.independent_groups,
                "root_lineages": witness_analysis.root_lineages,
                "independence_score": witness_analysis.independence_score,
                "correlation_penalty": witness_analysis.correlation_penalty,
            }
        else:
            witness_payload = dict(witness_analysis)

        payload = {
            "claim": claim.model_dump(mode="json"),
            "challenge_plan_id": challenge_plan_id,
            "witness_analysis": witness_payload,
            "warrant": warrant.model_dump(mode="json"),
            "belief_position": belief_position.model_dump(mode="json"),
            "decision_artifact": decision_artifact.model_dump(mode="json"),
            "stability_report": stability_report.model_dump(mode="json"),
            "counterfactual_report": counterfactual_report.model_dump(mode="json"),
            "source_snapshot_id": source_snapshot_id,
            "run_id": run_id,
            "proof_bundle_id": proof_bundle_id,
            "compiler_version": "epistemic-transaction-v2",
        }
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(
            transaction_id=f"txn:{digest}",
            claim=claim,
            challenge_plan_id=challenge_plan_id,
            witness_analysis=witness_payload,
            warrant=warrant,
            belief_position=belief_position,
            decision_artifact=decision_artifact,
            stability_report=stability_report,
            counterfactual_report=counterfactual_report,
            source_snapshot_id=source_snapshot_id,
            run_id=run_id,
            proof_bundle_id=proof_bundle_id,
        )

    @property
    def fingerprint(self) -> str:
        """Return a stable fingerprint of the complete computational transaction."""
        payload = self.model_dump(mode="json", exclude={"committed_event_id"})
        return hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    @property
    def ready_for_commit(self) -> bool:
        """Whether the computation is structurally complete enough for policy review."""
        return (
            self.belief_position.unresolved_challenges == 0
            and self.decision_artifact.final_decision in {DecisionState.ACCEPTED, DecisionState.HISTORICAL_ACCEPTED}
            and self.decision_artifact.final_decision is self.belief_position.decision
            and self.stability_report.baseline_decision == self.belief_position.decision.value
            and self.counterfactual_report.baseline_decision == self.belief_position.decision.value
        )

    def bind_commit(self, event_id: str) -> "EpistemicTransaction":
        """Return a new transaction bound to the durable commit event."""
        if not event_id:
            raise ValueError("event_id must not be empty")
        return self.model_copy(update={"committed_event_id": event_id})
