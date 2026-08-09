"""Independent verification of Thalos Prime proof bundles.

The verifier deliberately does not trust the runtime that produced a bundle.
It recomputes identifiers, source-span hashes, event-independent bundle roots,
and provenance integrity from serialized data.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from thalos_prime.epistemic_core import (
    EvidenceSpan,
    ProofBundle,
    SourceArtifact,
    canonical_json,
    sha256_hex,
)


class VerificationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str
    object_id: str | None = None


class ProofVerificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    bundle_id: str
    checked_claims: int = Field(ge=0)
    checked_evidence: int = Field(ge=0)
    issues: tuple[VerificationIssue, ...] = ()


class ProofBundleVerifier:
    """Verify a proof bundle against optionally supplied source artifacts."""

    def verify(
        self,
        bundle: ProofBundle,
        *,
        sources: dict[str, SourceArtifact] | None = None,
    ) -> ProofVerificationReport:
        issues: list[VerificationIssue] = []

        regenerated = ProofBundle.create(
            run_manifest=bundle.run_manifest,
            claims=bundle.claims,
            evidence=bundle.evidence,
            evaluations=bundle.evaluations,
            beliefs=bundle.beliefs,
            provenance_nodes=bundle.provenance_nodes,
            provenance_edges=bundle.provenance_edges,
            ledger_head_hash=bundle.ledger_head_hash,
        )
        if regenerated.proof_root != bundle.proof_root:
            issues.append(
                VerificationIssue(
                    code="proof_root_mismatch",
                    message="bundle proof root does not match canonical contents",
                    object_id=bundle.bundle_id,
                )
            )
        if bundle.bundle_id != f"proof:{bundle.proof_root}":
            issues.append(
                VerificationIssue(
                    code="bundle_id_mismatch",
                    message="bundle identifier does not match proof root",
                    object_id=bundle.bundle_id,
                )
            )

        claim_ids = {claim.claim_id for claim in bundle.claims}
        evidence_ids = {evidence.evidence_id for evidence in bundle.evidence}
        evaluation_ids = {evaluation.evaluation_id for evaluation in bundle.evaluations}

        for evaluation in bundle.evaluations:
            if evaluation.claim_id not in claim_ids:
                issues.append(
                    VerificationIssue(
                        code="evaluation_claim_missing",
                        message="evaluation references a claim absent from the bundle",
                        object_id=evaluation.evaluation_id,
                    )
                )
            referenced = set(evaluation.supporting_evidence + evaluation.contradicting_evidence)
            missing = sorted(referenced - evidence_ids)
            if missing:
                issues.append(
                    VerificationIssue(
                        code="evaluation_evidence_missing",
                        message=f"evaluation references missing evidence: {missing}",
                        object_id=evaluation.evaluation_id,
                    )
                )

        for belief in bundle.beliefs:
            if belief.claim_id not in claim_ids:
                issues.append(
                    VerificationIssue(
                        code="belief_claim_missing",
                        message="belief projection references a claim absent from the bundle",
                        object_id=belief.claim_id,
                    )
                )
            if (
                belief.latest_evaluation_id is not None
                and belief.latest_evaluation_id not in evaluation_ids
            ):
                issues.append(
                    VerificationIssue(
                        code="belief_evaluation_missing",
                        message="belief references an evaluation absent from the bundle",
                        object_id=belief.claim_id,
                    )
                )

        node_ids = {node.node_id for node in bundle.provenance_nodes}
        for edge in bundle.provenance_edges:
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                issues.append(
                    VerificationIssue(
                        code="provenance_endpoint_missing",
                        message="provenance edge references a missing node",
                        object_id=f"{edge.source_id}->{edge.target_id}",
                    )
                )

        if sources is not None:
            for evidence in bundle.evidence:
                artifact = sources.get(evidence.artifact_id)
                if artifact is None:
                    issues.append(
                        VerificationIssue(
                            code="source_missing",
                            message="source artifact required for span verification is missing",
                            object_id=evidence.evidence_id,
                        )
                    )
                    continue
                if not self._verify_span(evidence, artifact):
                    issues.append(
                        VerificationIssue(
                            code="source_span_invalid",
                            message="evidence text or hash does not match canonical source",
                            object_id=evidence.evidence_id,
                        )
                    )

        manifest_hash = bundle.run_manifest.manifest_hash
        if not manifest_hash.startswith("manifest:"):
            issues.append(
                VerificationIssue(
                    code="manifest_identity_invalid",
                    message="run manifest identity could not be derived",
                    object_id=bundle.run_manifest.run_id,
                )
            )

        return ProofVerificationReport(
            valid=not issues,
            bundle_id=bundle.bundle_id,
            checked_claims=len(bundle.claims),
            checked_evidence=len(bundle.evidence),
            issues=tuple(issues),
        )

    @staticmethod
    def _verify_span(evidence: EvidenceSpan, artifact: SourceArtifact) -> bool:
        if evidence.end > len(artifact.canonical_text) or evidence.start >= evidence.end:
            return False
        selected = artifact.canonical_text[evidence.start:evidence.end]
        return (
            evidence.artifact_id == artifact.artifact_id
            and selected == evidence.text
            and sha256_hex(selected) == evidence.text_hash
        )

    def verify_json(
        self,
        payload: str,
        *,
        sources: dict[str, SourceArtifact] | None = None,
    ) -> ProofVerificationReport:
        bundle = ProofBundle.model_validate_json(payload)
        return self.verify(bundle, sources=sources)

    @staticmethod
    def fingerprint(report: ProofVerificationReport) -> str:
        return sha256_hex(canonical_json(report.model_dump(mode="json")))


__all__ = [
    "ProofBundleVerifier",
    "ProofVerificationReport",
    "VerificationIssue",
]
