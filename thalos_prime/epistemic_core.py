"""Authoritative epistemic foundation for Thalos Prime v2.

This module is deliberately independent from ChatGPT, MCP, FastAPI, and any
specific model provider. It defines the primitives needed for reproducible
source-to-belief workflows:

- immutable source artifacts and frozen snapshots
- canonical claim/evidence identifiers
- evidence-span validation
- four-valued support state (supported/contradicted/both/neither)
- event-sourced belief transitions
- complete, tamper-evident event envelopes
- deterministic lexical retrieval with replay certificates
- provenance graphs and Merkle-rooted proof bundles
- run manifests that describe the execution environment

The module is a foundation, not a claim that semantic truth can be reduced to
one score. Model-assisted components may propose candidates; only explicit,
versioned policies may commit belief-state transitions.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Canonicalization and identifiers
# ---------------------------------------------------------------------------


def canonical_json(value: Any) -> str:
    """Return a stable JSON representation used for content addressing."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def sha256_hex(value: bytes | str) -> str:
    """Return a SHA-256 hex digest."""
    raw = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(raw).hexdigest()


def content_id(namespace: str, value: Any) -> str:
    """Create a deterministic namespaced content identifier."""
    return f"{namespace}:{sha256_hex(canonical_json(value))}"


def normalize_text(text: str) -> str:
    """Canonicalize text without pretending normalization preserves meaning."""
    return " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split()).strip()


def tokenize(text: str) -> tuple[str, ...]:
    """Tokenize text deterministically for the lexical retrieval baseline."""
    return tuple(sorted(set(re.findall(r"[a-z0-9]{2,}", text.lower()))))


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


class TrustClass(StrEnum):
    """Origin classification for source material."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    USER_ASSERTION = "user_assertion"
    SYNTHETIC = "synthetic_generated"
    UNKNOWN = "unknown"


class BeliefState(StrEnum):
    """Materialized state of a claim in the epistemic ledger."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DISPUTED = "disputed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


class SupportState(StrEnum):
    """Four-valued evidence state; avoids forcing mixed evidence into binary truth."""

    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    BOTH = "both"
    NEITHER = "neither"


class EventType(StrEnum):
    """Immutable epistemic ledger event types."""

    CLAIM_REGISTERED = "ClaimRegistered"
    EVIDENCE_ATTACHED = "EvidenceAttached"
    EVALUATION_RECORDED = "EvaluationRecorded"
    BELIEF_ACCEPTED = "BeliefAccepted"
    BELIEF_DISPUTED = "BeliefDisputed"
    BELIEF_REJECTED = "BeliefRejected"
    BELIEF_SUPERSEDED = "BeliefSuperseded"
    BELIEF_RETRACTED = "BeliefRetracted"


class SourceArtifact(BaseModel):
    """Immutable source artifact metadata; raw bytes live in object storage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    media_type: str
    canonical_text: str
    canonical_hash: str
    source_uri: str | None = None
    source_title: str | None = None
    issuer: str | None = None
    published_at: str | None = None
    retrieved_at: str | None = None
    trust_class: TrustClass = TrustClass.UNKNOWN
    eligible_as_evidence: bool = True

    @classmethod
    def create(
        cls,
        text: str,
        *,
        media_type: str = "text/plain",
        source_uri: str | None = None,
        source_title: str | None = None,
        issuer: str | None = None,
        published_at: str | None = None,
        retrieved_at: str | None = None,
        trust_class: TrustClass = TrustClass.UNKNOWN,
    ) -> "SourceArtifact":
        canonical = normalize_text(text)
        digest = sha256_hex(canonical)
        return cls(
            artifact_id=f"src:{digest}",
            media_type=media_type,
            canonical_text=canonical,
            canonical_hash=digest,
            source_uri=source_uri,
            source_title=source_title,
            issuer=issuer,
            published_at=published_at,
            retrieved_at=retrieved_at,
            trust_class=trust_class,
            eligible_as_evidence=trust_class is not TrustClass.SYNTHETIC,
        )


class SourceSnapshot(BaseModel):
    """Frozen collection of sources used by one reproducible execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: str
    artifact_ids: tuple[str, ...]
    merkle_root: str
    created_by_run: str

    @classmethod
    def create(cls, artifact_ids: Iterable[str], created_by_run: str) -> "SourceSnapshot":
        ids = tuple(sorted(set(artifact_ids)))
        root = merkle_root(ids)
        return cls(
            snapshot_id=f"snap:{sha256_hex(canonical_json({'ids': ids, 'root': root}))}",
            artifact_ids=ids,
            merkle_root=root,
            created_by_run=created_by_run,
        )


class Claim(BaseModel):
    """Atomic, scoped proposition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    text: str
    canonical_text: str
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    created_from_run: str | None = None

    @classmethod
    def create(
        cls,
        text: str,
        *,
        subject: str | None = None,
        predicate: str | None = None,
        object: str | None = None,
        valid_from: str | None = None,
        valid_to: str | None = None,
        created_from_run: str | None = None,
    ) -> "Claim":
        canonical = normalize_text(text)
        identity = {
            "canonical_text": canonical,
            "subject": subject,
            "predicate": predicate,
            "object": object,
            "valid_from": valid_from,
            "valid_to": valid_to,
        }
        return cls(
            claim_id=content_id("clm", identity),
            text=text,
            canonical_text=canonical,
            subject=subject,
            predicate=predicate,
            object=object,
            valid_from=valid_from,
            valid_to=valid_to,
            created_from_run=created_from_run,
        )


class EvidenceSpan(BaseModel):
    """Exact byte-independent evidence span anchored to canonical text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str
    artifact_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str
    text_hash: str
    extractor: str
    extractor_version: str

    @classmethod
    def create(
        cls,
        artifact: SourceArtifact,
        start: int,
        end: int,
        *,
        extractor: str = "manual",
        extractor_version: str = "1",
    ) -> "EvidenceSpan":
        if start >= end or end > len(artifact.canonical_text):
            raise ValueError("evidence span is outside canonical source bounds")
        text = artifact.canonical_text[start:end]
        evidence_identity = {
            "artifact_id": artifact.artifact_id,
            "start": start,
            "end": end,
            "text_hash": sha256_hex(text),
            "extractor": extractor,
            "extractor_version": extractor_version,
        }
        return cls(
            evidence_id=content_id("ev", evidence_identity),
            artifact_id=artifact.artifact_id,
            start=start,
            end=end,
            text=text,
            text_hash=sha256_hex(text),
            extractor=extractor,
            extractor_version=extractor_version,
        )


class EvidenceEvaluation(BaseModel):
    """Structured evaluation of a claim against evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: str
    claim_id: str
    supporting_evidence: tuple[str, ...] = ()
    contradicting_evidence: tuple[str, ...] = ()
    unresolved_dimensions: tuple[str, ...] = ()
    entailment: float = Field(ge=0.0, le=1.0)
    contradiction: float = Field(ge=0.0, le=1.0)
    temporal_validity: float = Field(ge=0.0, le=1.0)
    scope_validity: float = Field(ge=0.0, le=1.0)
    source_independence: float = Field(ge=0.0, le=1.0)
    support_state: SupportState
    evaluator: str
    evaluator_version: str

    @classmethod
    def create(
        cls,
        claim: Claim,
        *,
        supporting_evidence: Iterable[str] = (),
        contradicting_evidence: Iterable[str] = (),
        unresolved_dimensions: Iterable[str] = (),
        entailment: float = 0.0,
        contradiction: float = 0.0,
        temporal_validity: float = 0.0,
        scope_validity: float = 0.0,
        source_independence: float = 0.0,
        evaluator: str = "rule-based",
        evaluator_version: str = "1",
    ) -> "EvidenceEvaluation":
        support = tuple(sorted(set(supporting_evidence)))
        oppose = tuple(sorted(set(contradicting_evidence)))
        if support and oppose:
            state = SupportState.BOTH
        elif support:
            state = SupportState.SUPPORTED
        elif oppose:
            state = SupportState.CONTRADICTED
        else:
            state = SupportState.NEITHER
        identity = {
            "claim_id": claim.claim_id,
            "support": support,
            "oppose": oppose,
            "unresolved": tuple(sorted(set(unresolved_dimensions))),
            "entailment": entailment,
            "contradiction": contradiction,
            "temporal_validity": temporal_validity,
            "scope_validity": scope_validity,
            "source_independence": source_independence,
            "evaluator": evaluator,
            "evaluator_version": evaluator_version,
        }
        return cls(
            evaluation_id=content_id("eval", identity),
            claim_id=claim.claim_id,
            supporting_evidence=support,
            contradicting_evidence=oppose,
            unresolved_dimensions=tuple(sorted(set(unresolved_dimensions))),
            entailment=entailment,
            contradiction=contradiction,
            temporal_validity=temporal_validity,
            scope_validity=scope_validity,
            source_independence=source_independence,
            support_state=state,
            evaluator=evaluator,
            evaluator_version=evaluator_version,
        )


class DecisionPolicy(BaseModel):
    """Explicit policy controlling belief-state transitions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_id: str = "general-factual"
    version: str = "1"
    minimum_entailment: float = Field(default=0.8, ge=0.0, le=1.0)
    minimum_temporal_validity: float = Field(default=0.7, ge=0.0, le=1.0)
    minimum_scope_validity: float = Field(default=0.8, ge=0.0, le=1.0)
    minimum_source_independence: float = Field(default=0.5, ge=0.0, le=1.0)
    accept_only: tuple[SupportState, ...] = (SupportState.SUPPORTED,)

    @property
    def policy_hash(self) -> str:
        return content_id("policy", self.model_dump())

    def decide(self, evaluation: EvidenceEvaluation) -> BeliefState:
        """Map evaluation facts to a state without pretending this is universal truth."""
        if evaluation.support_state not in self.accept_only:
            if evaluation.support_state in (SupportState.BOTH, SupportState.CONTRADICTED):
                return BeliefState.DISPUTED
            return BeliefState.PENDING
        if evaluation.entailment < self.minimum_entailment:
            return BeliefState.PENDING
        if evaluation.temporal_validity < self.minimum_temporal_validity:
            return BeliefState.PENDING
        if evaluation.scope_validity < self.minimum_scope_validity:
            return BeliefState.PENDING
        if evaluation.source_independence < self.minimum_source_independence:
            return BeliefState.PENDING
        return BeliefState.ACCEPTED


class RunManifest(BaseModel):
    """Complete execution identity used for reproducible logical replay."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    query_hash: str
    corpus_snapshot_root: str
    canonicalizer_version: str = "1"
    retrieval_policy: str = "lexical-deterministic-v1"
    reasoning_policy: str = "claim-evaluation-v1"
    model_identity: Mapping[str, str | None] = Field(default_factory=dict)
    seed: int = 0
    code_commit: str = "unknown"
    dependency_lock_hash: str = "unknown"
    platform_identity: str = "python"

    @classmethod
    def create(
        cls,
        *,
        query: str,
        snapshot: SourceSnapshot,
        seed: int = 0,
        code_commit: str = "unknown",
        dependency_lock_hash: str = "unknown",
        model_identity: Mapping[str, str | None] | None = None,
    ) -> "RunManifest":
        query_hash = sha256_hex(normalize_text(query))
        identity = {
            "query_hash": query_hash,
            "snapshot_root": snapshot.merkle_root,
            "seed": seed,
            "code_commit": code_commit,
            "dependency_lock_hash": dependency_lock_hash,
            "model_identity": dict(model_identity or {}),
        }
        return cls(
            run_id=content_id("run", identity),
            query_hash=query_hash,
            corpus_snapshot_root=snapshot.merkle_root,
            seed=seed,
            code_commit=code_commit,
            dependency_lock_hash=dependency_lock_hash,
            model_identity=dict(model_identity or {}),
        )

    @property
    def manifest_hash(self) -> str:
        return content_id("manifest", self.model_dump())


class BeliefEvent(BaseModel):
    """Immutable domain event emitted by the belief reducer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    sequence: int = Field(ge=1)
    event_type: EventType
    claim_id: str
    payload: Mapping[str, Any]
    run_id: str
    policy_version: str
    previous_event_hash: str
    event_hash: str


class MaterializedBelief(BaseModel):
    """Current claim projection rebuilt solely from immutable events."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    state: BeliefState = BeliefState.PENDING
    latest_evaluation_id: str | None = None
    evidence_ids: tuple[str, ...] = ()
    superseded_by: str | None = None
    retraction_reason: str | None = None
    last_event_id: str | None = None


class ProvenanceNode(BaseModel):
    """A node in the derivation/provenance DAG."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str
    node_type: str
    payload_hash: str


class ProvenanceEdge(BaseModel):
    """A directed provenance relationship."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    target_id: str
    relation: str


class ProofBundle(BaseModel):
    """Portable machine-verifiable result package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str
    run_manifest: RunManifest
    claims: tuple[Claim, ...]
    evidence: tuple[EvidenceSpan, ...]
    evaluations: tuple[EvidenceEvaluation, ...]
    beliefs: tuple[MaterializedBelief, ...]
    provenance_nodes: tuple[ProvenanceNode, ...]
    provenance_edges: tuple[ProvenanceEdge, ...]
    ledger_head_hash: str
    proof_root: str

    @classmethod
    def create(
        cls,
        *,
        run_manifest: RunManifest,
        claims: Sequence[Claim],
        evidence: Sequence[EvidenceSpan],
        evaluations: Sequence[EvidenceEvaluation],
        beliefs: Sequence[MaterializedBelief],
        provenance_nodes: Sequence[ProvenanceNode] = (),
        provenance_edges: Sequence[ProvenanceEdge] = (),
        ledger_head_hash: str = "",
    ) -> "ProofBundle":
        payload = {
            "run_manifest": run_manifest.manifest_hash,
            "claims": [c.claim_id for c in sorted(claims, key=lambda x: x.claim_id)],
            "evidence": [e.evidence_id for e in sorted(evidence, key=lambda x: x.evidence_id)],
            "evaluations": [x.evaluation_id for x in sorted(evaluations, key=lambda x: x.evaluation_id)],
            "beliefs": [x.model_dump() for x in sorted(beliefs, key=lambda x: x.claim_id)],
            "nodes": [x.model_dump() for x in sorted(provenance_nodes, key=lambda x: x.node_id)],
            "edges": [x.model_dump() for x in sorted(provenance_edges, key=lambda x: (x.source_id, x.target_id, x.relation))],
            "ledger_head_hash": ledger_head_hash,
        }
        root = sha256_hex(canonical_json(payload))
        return cls(
            bundle_id=f"proof:{root}",
            run_manifest=run_manifest,
            claims=tuple(sorted(claims, key=lambda x: x.claim_id)),
            evidence=tuple(sorted(evidence, key=lambda x: x.evidence_id)),
            evaluations=tuple(sorted(evaluations, key=lambda x: x.evaluation_id)),
            beliefs=tuple(sorted(beliefs, key=lambda x: x.claim_id)),
            provenance_nodes=tuple(sorted(provenance_nodes, key=lambda x: x.node_id)),
            provenance_edges=tuple(sorted(provenance_edges, key=lambda x: (x.source_id, x.target_id, x.relation))),
            ledger_head_hash=ledger_head_hash,
            proof_root=root,
        )


# ---------------------------------------------------------------------------
# Merkle / provenance helpers
# ---------------------------------------------------------------------------


def merkle_root(values: Iterable[str]) -> str:
    """Compute a deterministic binary Merkle root over sorted leaf identifiers."""
    leaves = [sha256_hex(v) for v in sorted(set(values))]
    if not leaves:
        return sha256_hex("")
    while len(leaves) > 1:
        if len(leaves) % 2:
            leaves.append(leaves[-1])
        leaves = [
            sha256_hex(leaves[i] + leaves[i + 1])
            for i in range(0, len(leaves), 2)
        ]
    return leaves[0]


class ProvenanceGraph:
    """Small deterministic provenance DAG with cycle detection."""

    def __init__(self) -> None:
        self._nodes: dict[str, ProvenanceNode] = {}
        self._edges: set[tuple[str, str, str]] = set()

    def add_node(self, node_type: str, payload: Any, *, node_id: str | None = None) -> ProvenanceNode:
        identifier = node_id or content_id(node_type, payload)
        node = ProvenanceNode(
            node_id=identifier,
            node_type=node_type,
            payload_hash=sha256_hex(canonical_json(payload)),
        )
        self._nodes[identifier] = node
        return node

    def add_edge(self, source_id: str, target_id: str, relation: str) -> ProvenanceEdge:
        if source_id == target_id:
            raise ValueError("provenance self-edge is not permitted")
        if source_id not in self._nodes or target_id not in self._nodes:
            raise KeyError("both provenance nodes must exist before adding an edge")
        candidate = (source_id, target_id, relation)
        if self._would_cycle(source_id, target_id):
            raise ValueError("provenance edge would introduce a cycle")
        self._edges.add(candidate)
        return ProvenanceEdge(source_id=source_id, target_id=target_id, relation=relation)

    def _would_cycle(self, source_id: str, target_id: str) -> bool:
        adjacency: dict[str, set[str]] = {}
        for source, target, _ in self._edges:
            adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(source_id, set()).add(target_id)
        stack = [target_id]
        visited: set[str] = set()
        while stack:
            current = stack.pop()
            if current == source_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            stack.extend(sorted(adjacency.get(current, ())))
        return False

    def export(self) -> tuple[tuple[ProvenanceNode, ...], tuple[ProvenanceEdge, ...]]:
        nodes = tuple(sorted(self._nodes.values(), key=lambda x: x.node_id))
        edges = tuple(
            ProvenanceEdge(source_id=s, target_id=t, relation=r)
            for s, t, r in sorted(self._edges)
        )
        return nodes, edges


# ---------------------------------------------------------------------------
# Tamper-evident event log and deterministic ledger reducer
# ---------------------------------------------------------------------------


class EventLog:
    """Append-only event log whose hash covers the complete deterministic envelope."""

    def __init__(self) -> None:
        self._events: list[BeliefEvent] = []

    @property
    def head_hash(self) -> str:
        return self._events[-1].event_hash if self._events else ""

    @property
    def events(self) -> tuple[BeliefEvent, ...]:
        return tuple(self._events)

    def append(
        self,
        *,
        event_type: EventType,
        claim_id: str,
        payload: Mapping[str, Any],
        run_id: str,
        policy_version: str,
    ) -> BeliefEvent:
        sequence = len(self._events) + 1
        previous = self.head_hash
        identity = {
            "sequence": sequence,
            "event_type": event_type.value,
            "claim_id": claim_id,
            "payload": payload,
            "run_id": run_id,
            "policy_version": policy_version,
            "previous_event_hash": previous,
        }
        event_hash = sha256_hex(canonical_json(identity))
        event_id = f"evt:{event_hash}"
        event = BeliefEvent(
            event_id=event_id,
            sequence=sequence,
            event_type=event_type,
            claim_id=claim_id,
            payload=dict(payload),
            run_id=run_id,
            policy_version=policy_version,
            previous_event_hash=previous,
            event_hash=event_hash,
        )
        self._events.append(event)
        return event

    def verify(self) -> bool:
        previous = ""
        for expected_sequence, event in enumerate(self._events, start=1):
            if event.sequence != expected_sequence or event.previous_event_hash != previous:
                return False
            identity = {
                "sequence": event.sequence,
                "event_type": event.event_type.value,
                "claim_id": event.claim_id,
                "payload": event.payload,
                "run_id": event.run_id,
                "policy_version": event.policy_version,
                "previous_event_hash": event.previous_event_hash,
            }
            if sha256_hex(canonical_json(identity)) != event.event_hash:
                return False
            previous = event.event_hash
        return True


class BeliefLedger:
    """Event-sourced epistemic ledger with deterministic materialized projections."""

    def __init__(self) -> None:
        self._log = EventLog()
        self._claims: dict[str, Claim] = {}
        self._evaluations: dict[str, EvidenceEvaluation] = {}
        self._beliefs: dict[str, MaterializedBelief] = {}

    @property
    def event_log(self) -> EventLog:
        return self._log

    @property
    def head_hash(self) -> str:
        return self._log.head_hash

    def register_claim(self, claim: Claim, run_manifest: RunManifest, policy: DecisionPolicy) -> BeliefEvent:
        if claim.claim_id in self._claims:
            return self._log.events[-1]
        self._claims[claim.claim_id] = claim
        self._beliefs[claim.claim_id] = MaterializedBelief(claim_id=claim.claim_id)
        return self._log.append(
            event_type=EventType.CLAIM_REGISTERED,
            claim_id=claim.claim_id,
            payload={"claim": claim.model_dump()},
            run_id=run_manifest.run_id,
            policy_version=policy.version,
        )

    def attach_evidence(
        self,
        claim_id: str,
        evidence_ids: Iterable[str],
        run_manifest: RunManifest,
        policy: DecisionPolicy,
    ) -> BeliefEvent:
        if claim_id not in self._claims:
            raise KeyError(claim_id)
        ids = tuple(sorted(set(evidence_ids)))
        current = self._beliefs[claim_id]
        updated = current.model_copy(update={"evidence_ids": tuple(sorted(set(current.evidence_ids + ids)))})
        self._beliefs[claim_id] = updated
        return self._log.append(
            event_type=EventType.EVIDENCE_ATTACHED,
            claim_id=claim_id,
            payload={"evidence_ids": ids},
            run_id=run_manifest.run_id,
            policy_version=policy.version,
        )

    def record_evaluation(
        self,
        evaluation: EvidenceEvaluation,
        run_manifest: RunManifest,
        policy: DecisionPolicy,
    ) -> BeliefEvent:
        if evaluation.claim_id not in self._claims:
            raise KeyError(evaluation.claim_id)
        self._evaluations[evaluation.evaluation_id] = evaluation
        current = self._beliefs[evaluation.claim_id]
        updated = current.model_copy(update={"latest_evaluation_id": evaluation.evaluation_id})
        self._beliefs[evaluation.claim_id] = updated
        return self._log.append(
            event_type=EventType.EVALUATION_RECORDED,
            claim_id=evaluation.claim_id,
            payload={"evaluation": evaluation.model_dump()},
            run_id=run_manifest.run_id,
            policy_version=policy.version,
        )

    def commit_evaluation(
        self,
        claim_id: str,
        run_manifest: RunManifest,
        policy: DecisionPolicy,
    ) -> tuple[BeliefState, BeliefEvent]:
        belief = self._beliefs.get(claim_id)
        if belief is None:
            raise KeyError(claim_id)
        if belief.latest_evaluation_id is None:
            raise ValueError("claim has no evaluation to commit")
        evaluation = self._evaluations[belief.latest_evaluation_id]
        state = policy.decide(evaluation)
        event_type = {
            BeliefState.ACCEPTED: EventType.BELIEF_ACCEPTED,
            BeliefState.DISPUTED: EventType.BELIEF_DISPUTED,
            BeliefState.REJECTED: EventType.BELIEF_REJECTED,
            BeliefState.PENDING: EventType.EVALUATION_RECORDED,
        }[state]
        updated = belief.model_copy(update={"state": state, "last_event_id": "pending"})
        event = self._log.append(
            event_type=event_type,
            claim_id=claim_id,
            payload={"evaluation_id": evaluation.evaluation_id, "state": state.value},
            run_id=run_manifest.run_id,
            policy_version=policy.version,
        )
        self._beliefs[claim_id] = updated.model_copy(update={"last_event_id": event.event_id})
        return state, event

    def supersede(
        self,
        claim_id: str,
        replacement_claim_id: str,
        run_manifest: RunManifest,
        policy: DecisionPolicy,
    ) -> BeliefEvent:
        current = self._beliefs[claim_id]
        updated = current.model_copy(
            update={"state": BeliefState.SUPERSEDED, "superseded_by": replacement_claim_id}
        )
        event = self._log.append(
            event_type=EventType.BELIEF_SUPERSEDED,
            claim_id=claim_id,
            payload={"replacement_claim_id": replacement_claim_id},
            run_id=run_manifest.run_id,
            policy_version=policy.version,
        )
        self._beliefs[claim_id] = updated.model_copy(update={"last_event_id": event.event_id})
        return event

    def retract(
        self,
        claim_id: str,
        reason: str,
        run_manifest: RunManifest,
        policy: DecisionPolicy,
    ) -> BeliefEvent:
        current = self._beliefs[claim_id]
        event = self._log.append(
            event_type=EventType.BELIEF_RETRACTED,
            claim_id=claim_id,
            payload={"reason": reason},
            run_id=run_manifest.run_id,
            policy_version=policy.version,
        )
        self._beliefs[claim_id] = current.model_copy(
            update={
                "state": BeliefState.RETRACTED,
                "retraction_reason": reason,
                "last_event_id": event.event_id,
            }
        )
        return event

    def get_belief(self, claim_id: str) -> MaterializedBelief | None:
        return self._beliefs.get(claim_id)

    def rebuild(self) -> dict[str, MaterializedBelief]:
        """Rebuild materialized beliefs from the immutable event log."""
        claims: dict[str, Claim] = {}
        evaluations: dict[str, EvidenceEvaluation] = {}
        beliefs: dict[str, MaterializedBelief] = {}
        for event in self._log.events:
            if event.event_type is EventType.CLAIM_REGISTERED:
                claim = Claim.model_validate(event.payload["claim"])
                claims[claim.claim_id] = claim
                beliefs[claim.claim_id] = MaterializedBelief(claim_id=claim.claim_id, last_event_id=event.event_id)
            elif event.event_type is EventType.EVIDENCE_ATTACHED:
                current = beliefs[event.claim_id]
                ids = tuple(event.payload["evidence_ids"])
                beliefs[event.claim_id] = current.model_copy(
                    update={"evidence_ids": tuple(sorted(set(current.evidence_ids + ids))), "last_event_id": event.event_id}
                )
            elif event.event_type is EventType.EVALUATION_RECORDED:
                evaluation = EvidenceEvaluation.model_validate(event.payload["evaluation"])
                evaluations[evaluation.evaluation_id] = evaluation
                beliefs[event.claim_id] = beliefs[event.claim_id].model_copy(
                    update={"latest_evaluation_id": evaluation.evaluation_id, "last_event_id": event.event_id}
                )
            elif event.event_type in {
                EventType.BELIEF_ACCEPTED,
                EventType.BELIEF_DISPUTED,
                EventType.BELIEF_REJECTED,
            }:
                state = BeliefState(event.payload["state"])
                beliefs[event.claim_id] = beliefs[event.claim_id].model_copy(
                    update={"state": state, "last_event_id": event.event_id}
                )
            elif event.event_type is EventType.BELIEF_SUPERSEDED:
                beliefs[event.claim_id] = beliefs[event.claim_id].model_copy(
                    update={
                        "state": BeliefState.SUPERSEDED,
                        "superseded_by": str(event.payload["replacement_claim_id"]),
                        "last_event_id": event.event_id,
                    }
                )
            elif event.event_type is EventType.BELIEF_RETRACTED:
                beliefs[event.claim_id] = beliefs[event.claim_id].model_copy(
                    update={
                        "state": BeliefState.RETRACTED,
                        "retraction_reason": str(event.payload["reason"]),
                        "last_event_id": event.event_id,
                    }
                )
        if not self._log.verify():
            raise ValueError("event log integrity verification failed")
        self._claims = claims
        self._evaluations = evaluations
        self._beliefs = beliefs
        return dict(beliefs)

    def snapshot(self) -> tuple[MaterializedBelief, ...]:
        return tuple(sorted(self._beliefs.values(), key=lambda x: x.claim_id))


# ---------------------------------------------------------------------------
# Evidence validation and deterministic retrieval
# ---------------------------------------------------------------------------


class EvidenceValidator:
    """Validate source spans and synthetic/untrusted evidence boundaries."""

    @staticmethod
    def validate_span(evidence: EvidenceSpan, artifact: SourceArtifact) -> bool:
        if evidence.artifact_id != artifact.artifact_id:
            return False
        if evidence.end > len(artifact.canonical_text):
            return False
        expected = artifact.canonical_text[evidence.start:evidence.end]
        return expected == evidence.text and sha256_hex(expected) == evidence.text_hash

    @staticmethod
    def can_support_claim(artifact: SourceArtifact) -> bool:
        return artifact.eligible_as_evidence and artifact.trust_class is not TrustClass.SYNTHETIC


class RetrievalHit(BaseModel):
    """Deterministic retrieval result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    score: float
    matched_terms: tuple[str, ...]


class RetrievalCertificate(BaseModel):
    """Replay metadata for a deterministic retrieval operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query_hash: str
    snapshot_root: str
    policy: str
    candidate_ids: tuple[str, ...]
    ranked_ids: tuple[str, ...]
    certificate_hash: str


class DeterministicRetriever:
    """Dependency-light lexical baseline with stable tie-breaking."""

    def search(
        self,
        query: str,
        artifacts: Sequence[SourceArtifact],
        *,
        snapshot: SourceSnapshot | None = None,
        limit: int = 20,
    ) -> tuple[tuple[RetrievalHit, ...], RetrievalCertificate]:
        if limit < 1:
            raise ValueError("limit must be positive")
        q_terms = set(tokenize(query))
        candidates = [a for a in artifacts if a.eligible_as_evidence]
        if snapshot is not None:
            allowed = set(snapshot.artifact_ids)
            candidates = [a for a in candidates if a.artifact_id in allowed]
        hits: list[RetrievalHit] = []
        for artifact in candidates:
            terms = set(tokenize(artifact.canonical_text))
            matched = tuple(sorted(q_terms & terms))
            if not matched:
                continue
            denominator = math.sqrt(max(1, len(q_terms) * len(terms)))
            score = len(matched) / denominator
            hits.append(
                RetrievalHit(
                    artifact_id=artifact.artifact_id,
                    score=score,
                    matched_terms=matched,
                )
            )
        ranked = tuple(sorted(hits, key=lambda x: (-x.score, x.artifact_id))[:limit])
        candidate_ids = tuple(sorted(a.artifact_id for a in candidates))
        ranked_ids = tuple(x.artifact_id for x in ranked)
        snapshot_root = snapshot.merkle_root if snapshot else merkle_root(candidate_ids)
        certificate_payload = {
            "query_hash": sha256_hex(normalize_text(query)),
            "snapshot_root": snapshot_root,
            "policy": "lexical-deterministic-v1",
            "candidate_ids": candidate_ids,
            "ranked_ids": ranked_ids,
        }
        certificate = RetrievalCertificate(
            **certificate_payload,
            certificate_hash=sha256_hex(canonical_json(certificate_payload)),
        )
        return ranked, certificate


# ---------------------------------------------------------------------------
# Top-level engine
# ---------------------------------------------------------------------------


@dataclass
class ThalosEpistemicEngine:
    """Small orchestration facade for the v2 epistemic primitives."""

    ledger: BeliefLedger = field(default_factory=BeliefLedger)
    retriever: DeterministicRetriever = field(default_factory=DeterministicRetriever)
    validator: EvidenceValidator = field(default_factory=EvidenceValidator)

    def evaluate_and_commit(
        self,
        *,
        claim: Claim,
        evaluation: EvidenceEvaluation,
        run_manifest: RunManifest,
        policy: DecisionPolicy,
    ) -> tuple[BeliefState, BeliefEvent]:
        self.ledger.register_claim(claim, run_manifest, policy)
        self.ledger.attach_evidence(
            claim.claim_id,
            evaluation.supporting_evidence + evaluation.contradicting_evidence,
            run_manifest,
            policy,
        )
        self.ledger.record_evaluation(evaluation, run_manifest, policy)
        return self.ledger.commit_evaluation(claim.claim_id, run_manifest, policy)

    def build_proof_bundle(
        self,
        *,
        run_manifest: RunManifest,
        claims: Sequence[Claim],
        evidence: Sequence[EvidenceSpan],
        evaluations: Sequence[EvidenceEvaluation],
        provenance: ProvenanceGraph,
    ) -> ProofBundle:
        nodes, edges = provenance.export()
        return ProofBundle.create(
            run_manifest=run_manifest,
            claims=claims,
            evidence=evidence,
            evaluations=evaluations,
            beliefs=self.ledger.snapshot(),
            provenance_nodes=nodes,
            provenance_edges=edges,
            ledger_head_hash=self.ledger.head_hash,
        )


__all__ = [
    "BeliefEvent",
    "BeliefLedger",
    "BeliefState",
    "Claim",
    "DecisionPolicy",
    "DeterministicRetriever",
    "EvidenceEvaluation",
    "EvidenceSpan",
    "EvidenceValidator",
    "EventLog",
    "EventType",
    "MaterializedBelief",
    "ProofBundle",
    "ProvenanceEdge",
    "ProvenanceGraph",
    "ProvenanceNode",
    "RetrievalCertificate",
    "RetrievalHit",
    "RunManifest",
    "SourceArtifact",
    "SourceSnapshot",
    "SupportState",
    "ThalosEpistemicEngine",
    "TrustClass",
    "canonical_json",
    "content_id",
    "merkle_root",
    "normalize_text",
    "sha256_hex",
]
