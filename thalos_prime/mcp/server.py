"""MCP server exposing Thalos Prime epistemic transactions.

The server is intentionally thin. It translates MCP requests into typed domain
operations and returns structured records. It does not contain epistemic rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from thalos_prime.epistemic_core import (
    BeliefState,
    Claim,
    DecisionPolicy,
    EvidenceEvaluation,
    EvidenceSpan,
    ProvenanceGraph,
    RunManifest,
    SourceArtifact,
    SourceSnapshot,
    ThalosEpistemicEngine,
    TrustClass,
)

try:  # Optional dependency; the core remains usable without MCP installed.
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised only when optional MCP is absent
    FastMCP = None  # type: ignore[assignment,misc]


@dataclass
class ThalosMcpRuntime:
    """In-process MCP runtime state.

    Production deployments should replace these dictionaries with durable
    repositories backed by an object store and event database. Their explicit
    shape makes that replacement straightforward.
    """

    engine: ThalosEpistemicEngine = field(default_factory=ThalosEpistemicEngine)
    artifacts: dict[str, SourceArtifact] = field(default_factory=dict)
    snapshots: dict[str, SourceSnapshot] = field(default_factory=dict)
    claims: dict[str, Claim] = field(default_factory=dict)
    evidence: dict[str, EvidenceSpan] = field(default_factory=dict)
    evaluations: dict[str, EvidenceEvaluation] = field(default_factory=dict)
    manifests: dict[str, RunManifest] = field(default_factory=dict)
    provenance: ProvenanceGraph = field(default_factory=ProvenanceGraph)

    def ingest_artifact(
        self,
        *,
        text: str,
        media_type: str = "text/plain",
        source_uri: str | None = None,
        source_title: str | None = None,
        issuer: str | None = None,
        published_at: str | None = None,
        retrieved_at: str | None = None,
        trust_class: str = TrustClass.UNKNOWN.value,
    ) -> dict[str, Any]:
        artifact = SourceArtifact.create(
            text,
            media_type=media_type,
            source_uri=source_uri,
            source_title=source_title,
            issuer=issuer,
            published_at=published_at,
            retrieved_at=retrieved_at,
            trust_class=TrustClass(trust_class),
        )
        self.artifacts[artifact.artifact_id] = artifact
        self.provenance.add_node("source", artifact.model_dump(), node_id=artifact.artifact_id)
        return artifact.model_dump(mode="json")

    def create_snapshot(self, *, artifact_ids: list[str], created_by_run: str) -> dict[str, Any]:
        missing = sorted(set(artifact_ids) - self.artifacts.keys())
        if missing:
            raise KeyError(f"unknown artifact_ids: {missing}")
        snapshot = SourceSnapshot.create(artifact_ids, created_by_run=created_by_run)
        self.snapshots[snapshot.snapshot_id] = snapshot
        return snapshot.model_dump(mode="json")

    def create_run(
        self,
        *,
        query: str,
        snapshot_id: str,
        seed: int = 0,
        code_commit: str = "unknown",
        dependency_lock_hash: str = "unknown",
        model_identity: dict[str, str | None] | None = None,
    ) -> dict[str, Any]:
        snapshot = self.snapshots[snapshot_id]
        manifest = RunManifest.create(
            query=query,
            snapshot=snapshot,
            seed=seed,
            code_commit=code_commit,
            dependency_lock_hash=dependency_lock_hash,
            model_identity=model_identity,
        )
        self.manifests[manifest.run_id] = manifest
        return manifest.model_dump(mode="json")

    def search(
        self,
        *,
        query: str,
        snapshot_id: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        snapshot = self.snapshots[snapshot_id]
        artifacts = [self.artifacts[artifact_id] for artifact_id in snapshot.artifact_ids]
        hits, certificate = self.engine.retriever.search(
            query,
            artifacts,
            snapshot=snapshot,
            limit=limit,
        )
        return {
            "hits": [hit.model_dump(mode="json") for hit in hits],
            "retrieval_certificate": certificate.model_dump(mode="json"),
        }

    def register_claim(
        self,
        *,
        text: str,
        run_id: str,
        subject: str | None = None,
        predicate: str | None = None,
        object: str | None = None,
        valid_from: str | None = None,
        valid_to: str | None = None,
    ) -> dict[str, Any]:
        manifest = self.manifests[run_id]
        claim = Claim.create(
            text,
            subject=subject,
            predicate=predicate,
            object=object,
            valid_from=valid_from,
            valid_to=valid_to,
            created_from_run=run_id,
        )
        self.claims[claim.claim_id] = claim
        policy = DecisionPolicy()
        self.engine.ledger.register_claim(claim, manifest, policy)
        self.provenance.add_node("claim", claim.model_dump(), node_id=claim.claim_id)
        return claim.model_dump(mode="json")

    def bind_evidence(
        self,
        *,
        artifact_id: str,
        start: int,
        end: int,
        extractor: str = "manual",
        extractor_version: str = "1",
    ) -> dict[str, Any]:
        artifact = self.artifacts[artifact_id]
        evidence = EvidenceSpan.create(
            artifact,
            start,
            end,
            extractor=extractor,
            extractor_version=extractor_version,
        )
        if not self.engine.validator.validate_span(evidence, artifact):
            raise ValueError("evidence span failed source binding validation")
        self.evidence[evidence.evidence_id] = evidence
        self.provenance.add_node("evidence", evidence.model_dump(), node_id=evidence.evidence_id)
        self.provenance.add_edge(artifact_id, evidence.evidence_id, "contains")
        return evidence.model_dump(mode="json")

    def evaluate_claim(
        self,
        *,
        claim_id: str,
        supporting_evidence: list[str] | None = None,
        contradicting_evidence: list[str] | None = None,
        unresolved_dimensions: list[str] | None = None,
        entailment: float = 0.0,
        contradiction: float = 0.0,
        temporal_validity: float = 0.0,
        scope_validity: float = 0.0,
        source_independence: float = 0.0,
        evaluator: str = "external-verifier",
        evaluator_version: str = "1",
    ) -> dict[str, Any]:
        claim = self.claims[claim_id]
        support = supporting_evidence or []
        oppose = contradicting_evidence or []
        unknown = sorted(set(support + oppose) - self.evidence.keys())
        if unknown:
            raise KeyError(f"unknown evidence_ids: {unknown}")
        evaluation = EvidenceEvaluation.create(
            claim,
            supporting_evidence=support,
            contradicting_evidence=oppose,
            unresolved_dimensions=unresolved_dimensions or [],
            entailment=entailment,
            contradiction=contradiction,
            temporal_validity=temporal_validity,
            scope_validity=scope_validity,
            source_independence=source_independence,
            evaluator=evaluator,
            evaluator_version=evaluator_version,
        )
        self.evaluations[evaluation.evaluation_id] = evaluation
        for evidence_id in support:
            self.provenance.add_edge(evidence_id, claim_id, "supports")
        for evidence_id in oppose:
            self.provenance.add_edge(evidence_id, claim_id, "contradicts")
        return evaluation.model_dump(mode="json")

    def commit_belief(
        self,
        *,
        claim_id: str,
        evaluation_id: str,
        run_id: str,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        claim = self.claims[claim_id]
        evaluation = self.evaluations[evaluation_id]
        if evaluation.claim_id != claim_id:
            raise ValueError("evaluation does not belong to claim")
        manifest = self.manifests[run_id]
        decision_policy = DecisionPolicy.model_validate(policy or {})
        self.engine.ledger.attach_evidence(
            claim_id,
            evaluation.supporting_evidence + evaluation.contradicting_evidence,
            manifest,
            decision_policy,
        )
        self.engine.ledger.record_evaluation(evaluation, manifest, decision_policy)
        state, event = self.engine.ledger.commit_evaluation(
            claim_id,
            manifest,
            decision_policy,
        )
        return {
            "claim_id": claim_id,
            "state": state.value,
            "event": event.model_dump(mode="json"),
            "policy_hash": decision_policy.policy_hash,
        }

    def get_belief(self, *, claim_id: str) -> dict[str, Any]:
        belief = self.engine.ledger.get_belief(claim_id)
        if belief is None:
            raise KeyError(claim_id)
        return belief.model_dump(mode="json")

    def trace_claim(self, *, claim_id: str) -> dict[str, Any]:
        events = [
            event.model_dump(mode="json")
            for event in self.engine.ledger.event_log.events
            if event.claim_id == claim_id
        ]
        return {
            "claim": self.claims[claim_id].model_dump(mode="json"),
            "belief": self.get_belief(claim_id=claim_id),
            "events": events,
            "ledger_head_hash": self.engine.ledger.head_hash,
            "ledger_integrity": self.engine.ledger.event_log.verify(),
        }

    def export_proof(self, *, run_id: str, claim_ids: list[str]) -> dict[str, Any]:
        manifest = self.manifests[run_id]
        claims = [self.claims[claim_id] for claim_id in sorted(set(claim_ids))]
        evaluation_ids = {
            belief.latest_evaluation_id
            for claim in claims
            if (belief := self.engine.ledger.get_belief(claim.claim_id)) is not None
            and belief.latest_evaluation_id is not None
        }
        evaluations = [self.evaluations[evaluation_id] for evaluation_id in sorted(evaluation_ids)]
        evidence_ids = {
            evidence_id
            for evaluation in evaluations
            for evidence_id in (
                evaluation.supporting_evidence + evaluation.contradicting_evidence
            )
        }
        evidence = [self.evidence[evidence_id] for evidence_id in sorted(evidence_ids)]
        bundle = self.engine.build_proof_bundle(
            run_manifest=manifest,
            claims=claims,
            evidence=evidence,
            evaluations=evaluations,
            provenance=self.provenance,
        )
        return bundle.model_dump(mode="json")


def create_mcp_server(runtime: ThalosMcpRuntime | None = None) -> Any:
    """Create a FastMCP server when the optional MCP package is installed."""
    if FastMCP is None:
        raise RuntimeError(
            "MCP support is not installed. Install the optional 'mcp' dependency."
        )
    state = runtime or ThalosMcpRuntime()
    mcp = FastMCP("Thalos Prime")

    mcp.tool(name="thalos.artifact.ingest")(state.ingest_artifact)
    mcp.tool(name="thalos.snapshot.create")(state.create_snapshot)
    mcp.tool(name="thalos.run.create")(state.create_run)
    mcp.tool(name="thalos.search")(state.search)
    mcp.tool(name="thalos.claim.register")(state.register_claim)
    mcp.tool(name="thalos.evidence.bind")(state.bind_evidence)
    mcp.tool(name="thalos.claim.evaluate")(state.evaluate_claim)
    mcp.tool(name="thalos.belief.commit")(state.commit_belief)
    mcp.tool(name="thalos.belief.get")(state.get_belief)
    mcp.tool(name="thalos.audit.trace")(state.trace_claim)
    mcp.tool(name="thalos.proof.export")(state.export_proof)
    return mcp


def main() -> None:
    """Launch the MCP server using the transport selected by FastMCP."""
    server = create_mcp_server()
    server.run()


if __name__ == "__main__":
    main()
