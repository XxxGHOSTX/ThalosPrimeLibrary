"""Tests for the authoritative Thalos Prime epistemic foundation."""

from __future__ import annotations

from thalos_prime.epistemic_core import (
    BeliefState,
    Claim,
    DecisionPolicy,
    DeterministicRetriever,
    EvidenceEvaluation,
    EvidenceSpan,
    EvidenceValidator,
    ProvenanceGraph,
    RunManifest,
    SourceArtifact,
    SourceSnapshot,
    SupportState,
    ThalosEpistemicEngine,
    TrustClass,
)


def _fixture_run() -> tuple[SourceArtifact, SourceSnapshot, RunManifest]:
    source = SourceArtifact.create(
        "The audited report states that revenue increased by five percent in 2025.",
        source_uri="https://example.test/report",
        source_title="Audited report",
        issuer="Example Corp",
        published_at="2026-01-10",
        trust_class=TrustClass.PRIMARY,
    )
    snapshot = SourceSnapshot.create([source.artifact_id], created_by_run="bootstrap")
    manifest = RunManifest.create(query="Did revenue increase?", snapshot=snapshot, seed=7)
    return source, snapshot, manifest


def test_source_identity_is_content_addressed() -> None:
    first = SourceArtifact.create("same text", trust_class=TrustClass.PRIMARY)
    second = SourceArtifact.create("same   text", trust_class=TrustClass.PRIMARY)
    assert first.artifact_id == second.artifact_id
    assert first.canonical_hash == second.canonical_hash


def test_synthetic_artifacts_cannot_support_claims() -> None:
    artifact = SourceArtifact.create(
        "A generated sentence that happens to look factual.",
        trust_class=TrustClass.SYNTHETIC,
    )
    assert artifact.eligible_as_evidence is False
    assert EvidenceValidator.can_support_claim(artifact) is False


def test_evidence_span_is_exactly_bound_to_source() -> None:
    source, _, _ = _fixture_run()
    start = source.canonical_text.index("revenue")
    end = source.canonical_text.index(" in 2025")
    evidence = EvidenceSpan.create(source, start, end)
    assert evidence.text == "revenue increased by five percent"
    assert EvidenceValidator.validate_span(evidence, source)


def test_snapshot_is_order_independent() -> None:
    a = SourceArtifact.create("alpha", trust_class=TrustClass.PRIMARY)
    b = SourceArtifact.create("beta", trust_class=TrustClass.PRIMARY)
    left = SourceSnapshot.create([a.artifact_id, b.artifact_id], created_by_run="x")
    right = SourceSnapshot.create([b.artifact_id, a.artifact_id], created_by_run="x")
    assert left.merkle_root == right.merkle_root
    assert left.snapshot_id == right.snapshot_id


def test_four_valued_support_state() -> None:
    claim = Claim.create("Revenue increased.")
    supported = EvidenceEvaluation.create(claim, supporting_evidence=["ev:1"])
    contradicted = EvidenceEvaluation.create(claim, contradicting_evidence=["ev:2"])
    both = EvidenceEvaluation.create(
        claim,
        supporting_evidence=["ev:1"],
        contradicting_evidence=["ev:2"],
    )
    neither = EvidenceEvaluation.create(claim)
    assert supported.support_state is SupportState.SUPPORTED
    assert contradicted.support_state is SupportState.CONTRADICTED
    assert both.support_state is SupportState.BOTH
    assert neither.support_state is SupportState.NEITHER


def test_policy_accepts_only_sufficient_supported_evidence() -> None:
    source, _, manifest = _fixture_run()
    claim = Claim.create("Revenue increased by five percent in 2025.")
    evidence = EvidenceSpan.create(source, 0, len(source.canonical_text))
    evaluation = EvidenceEvaluation.create(
        claim,
        supporting_evidence=[evidence.evidence_id],
        entailment=0.95,
        contradiction=0.0,
        temporal_validity=1.0,
        scope_validity=0.95,
        source_independence=0.8,
    )
    engine = ThalosEpistemicEngine()
    state, _ = engine.evaluate_and_commit(
        claim=claim,
        evaluation=evaluation,
        run_manifest=manifest,
        policy=DecisionPolicy(),
    )
    assert state is BeliefState.ACCEPTED
    assert engine.ledger.event_log.verify()
    rebuilt = engine.ledger.rebuild()
    assert rebuilt[claim.claim_id].state is BeliefState.ACCEPTED


def test_conflicting_evidence_is_disputed() -> None:
    _, _, manifest = _fixture_run()
    claim = Claim.create("Revenue increased.")
    evaluation = EvidenceEvaluation.create(
        claim,
        supporting_evidence=["ev:support"],
        contradicting_evidence=["ev:oppose"],
        entailment=0.9,
        contradiction=0.9,
        temporal_validity=1.0,
        scope_validity=1.0,
        source_independence=1.0,
    )
    engine = ThalosEpistemicEngine()
    state, _ = engine.evaluate_and_commit(
        claim=claim,
        evaluation=evaluation,
        run_manifest=manifest,
        policy=DecisionPolicy(),
    )
    assert state is BeliefState.DISPUTED


def test_retrieval_is_stable_and_snapshot_bound() -> None:
    a = SourceArtifact.create("alpha revenue report", trust_class=TrustClass.PRIMARY)
    b = SourceArtifact.create("beta weather report", trust_class=TrustClass.PRIMARY)
    c = SourceArtifact.create("synthetic revenue claim", trust_class=TrustClass.SYNTHETIC)
    snapshot = SourceSnapshot.create([a.artifact_id, b.artifact_id], created_by_run="r")
    retriever = DeterministicRetriever()
    first_hits, first_cert = retriever.search(
        "revenue report", [b, c, a], snapshot=snapshot
    )
    second_hits, second_cert = retriever.search(
        "revenue report", [a, b, c], snapshot=snapshot
    )
    assert first_hits == second_hits
    assert first_cert == second_cert
    assert c.artifact_id not in first_cert.candidate_ids


def test_provenance_graph_rejects_cycles() -> None:
    graph = ProvenanceGraph()
    source = graph.add_node("source", {"id": "src:1"}, node_id="src:1")
    claim = graph.add_node("claim", {"id": "clm:1"}, node_id="clm:1")
    graph.add_edge(source.node_id, claim.node_id, "supports")
    try:
        graph.add_edge(claim.node_id, source.node_id, "derived_from")
    except ValueError:
        pass
    else:
        raise AssertionError("expected cycle rejection")


def test_proof_bundle_is_reproducible() -> None:
    source, _, manifest = _fixture_run()
    claim = Claim.create("Revenue increased by five percent in 2025.")
    evidence = EvidenceSpan.create(source, 0, len(source.canonical_text))
    evaluation = EvidenceEvaluation.create(
        claim,
        supporting_evidence=[evidence.evidence_id],
        entailment=1.0,
        temporal_validity=1.0,
        scope_validity=1.0,
        source_independence=1.0,
    )
    engine = ThalosEpistemicEngine()
    engine.evaluate_and_commit(
        claim=claim,
        evaluation=evaluation,
        run_manifest=manifest,
        policy=DecisionPolicy(),
    )
    graph = ProvenanceGraph()
    graph.add_node("source", source.model_dump(), node_id=source.artifact_id)
    graph.add_node("evidence", evidence.model_dump(), node_id=evidence.evidence_id)
    graph.add_node("claim", claim.model_dump(), node_id=claim.claim_id)
    graph.add_edge(source.artifact_id, evidence.evidence_id, "contains")
    graph.add_edge(evidence.evidence_id, claim.claim_id, "supports")
    first = engine.build_proof_bundle(
        run_manifest=manifest,
        claims=[claim],
        evidence=[evidence],
        evaluations=[evaluation],
        provenance=graph,
    )
    second = engine.build_proof_bundle(
        run_manifest=manifest,
        claims=[claim],
        evidence=[evidence],
        evaluations=[evaluation],
        provenance=graph,
    )
    assert first.bundle_id == second.bundle_id
    assert first.proof_root == second.proof_root
