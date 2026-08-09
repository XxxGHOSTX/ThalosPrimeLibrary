"""Persistent MCP runtime backed by :mod:`sqlite_store`.

This adapter preserves the thin MCP boundary while making the runtime durable.
Domain decisions remain in ``epistemic_core``; this module handles hydration,
transactional persistence, idempotency, and optimistic concurrency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, TypeVar

from thalos_prime.epistemic_core import (
    Claim,
    EvidenceEvaluation,
    EvidenceSpan,
    ProofBundle,
    RunManifest,
    SourceArtifact,
    SourceSnapshot,
)
from thalos_prime.mcp.server import ThalosMcpRuntime
from thalos_prime.persistence.sqlite_store import SqliteEpistemicStore

_T = TypeVar("_T", bound=Mapping[str, Any])


class PersistentThalosMcpRuntime(ThalosMcpRuntime):
    """MCP runtime with restart-safe repositories and event persistence."""

    def __init__(self, database_path: str | Path) -> None:
        super().__init__()
        self.store = SqliteEpistemicStore(database_path)
        self._hydrate()

    def close(self) -> None:
        """Close durable resources."""
        self.store.close()

    def _hydrate(self) -> None:
        self.artifacts = {
            item.artifact_id: item
            for raw in self.store.list_records("artifact")
            if (item := SourceArtifact.model_validate(raw))
        }
        self.snapshots = {
            item.snapshot_id: item
            for raw in self.store.list_records("snapshot")
            if (item := SourceSnapshot.model_validate(raw))
        }
        self.claims = {
            item.claim_id: item
            for raw in self.store.list_records("claim")
            if (item := Claim.model_validate(raw))
        }
        self.evidence = {
            item.evidence_id: item
            for raw in self.store.list_records("evidence")
            if (item := EvidenceSpan.model_validate(raw))
        }
        self.evaluations = {
            item.evaluation_id: item
            for raw in self.store.list_records("evaluation")
            if (item := EvidenceEvaluation.model_validate(raw))
        }
        self.manifests = {
            item.run_id: item
            for raw in self.store.list_records("manifest")
            if (item := RunManifest.model_validate(raw))
        }

        events = list(self.store.load_events())
        # EventLog intentionally exposes immutable public views; hydration is a
        # persistence concern, so the adapter restores the private backing list
        # and immediately verifies/rebuilds all projections.
        self.engine.ledger.event_log._events = events  # noqa: SLF001
        if events:
            self.engine.ledger.rebuild()

        for artifact in self.artifacts.values():
            self.provenance.add_node(
                "source", artifact.model_dump(), node_id=artifact.artifact_id
            )
        for claim in self.claims.values():
            self.provenance.add_node("claim", claim.model_dump(), node_id=claim.claim_id)
        for evidence in self.evidence.values():
            self.provenance.add_node(
                "evidence", evidence.model_dump(), node_id=evidence.evidence_id
            )
            if evidence.artifact_id in self.artifacts:
                self.provenance.add_edge(
                    evidence.artifact_id, evidence.evidence_id, "contains"
                )
        for evaluation in self.evaluations.values():
            for evidence_id in evaluation.supporting_evidence:
                if evidence_id in self.evidence and evaluation.claim_id in self.claims:
                    self.provenance.add_edge(evidence_id, evaluation.claim_id, "supports")
            for evidence_id in evaluation.contradicting_evidence:
                if evidence_id in self.evidence and evaluation.claim_id in self.claims:
                    self.provenance.add_edge(
                        evidence_id, evaluation.claim_id, "contradicts"
                    )

    def _persist_new_events(self, previous_version: int) -> None:
        events = self.engine.ledger.event_log.events
        expected = previous_version
        for event in events[previous_version:]:
            self.store.append_event(event, expected_version=expected)
            expected += 1

    def _idempotent(
        self,
        operation: str,
        idempotency_key: str | None,
        request: Mapping[str, Any],
        execute: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        if not idempotency_key:
            return execute()
        previous = self.store.get_idempotent_response(
            operation, idempotency_key, request
        )
        if previous is not None:
            return previous
        response = execute()
        self.store.save_idempotent_response(
            operation, idempotency_key, request, response
        )
        return response

    def ingest_artifact(self, *, idempotency_key: str | None = None, **kwargs: Any) -> dict[str, Any]:
        request = dict(kwargs)

        def execute() -> dict[str, Any]:
            response = super(PersistentThalosMcpRuntime, self).ingest_artifact(**kwargs)
            artifact = SourceArtifact.model_validate(response)
            self.store.put_record("artifact", artifact.artifact_id, response)
            return response

        return self._idempotent("artifact.ingest", idempotency_key, request, execute)

    def create_snapshot(self, *, idempotency_key: str | None = None, **kwargs: Any) -> dict[str, Any]:
        request = dict(kwargs)

        def execute() -> dict[str, Any]:
            response = super(PersistentThalosMcpRuntime, self).create_snapshot(**kwargs)
            snapshot = SourceSnapshot.model_validate(response)
            self.store.put_record("snapshot", snapshot.snapshot_id, response)
            return response

        return self._idempotent("snapshot.create", idempotency_key, request, execute)

    def create_run(self, *, idempotency_key: str | None = None, **kwargs: Any) -> dict[str, Any]:
        request = dict(kwargs)

        def execute() -> dict[str, Any]:
            response = super(PersistentThalosMcpRuntime, self).create_run(**kwargs)
            manifest = RunManifest.model_validate(response)
            self.store.put_record("manifest", manifest.run_id, response)
            return response

        return self._idempotent("run.create", idempotency_key, request, execute)

    def register_claim(self, *, idempotency_key: str | None = None, **kwargs: Any) -> dict[str, Any]:
        request = dict(kwargs)

        def execute() -> dict[str, Any]:
            previous = self.store.stream_version()
            response = super(PersistentThalosMcpRuntime, self).register_claim(**kwargs)
            claim = Claim.model_validate(response)
            self.store.put_record("claim", claim.claim_id, response)
            self._persist_new_events(previous)
            return response

        return self._idempotent("claim.register", idempotency_key, request, execute)

    def bind_evidence(self, *, idempotency_key: str | None = None, **kwargs: Any) -> dict[str, Any]:
        request = dict(kwargs)

        def execute() -> dict[str, Any]:
            response = super(PersistentThalosMcpRuntime, self).bind_evidence(**kwargs)
            evidence = EvidenceSpan.model_validate(response)
            self.store.put_record("evidence", evidence.evidence_id, response)
            return response

        return self._idempotent("evidence.bind", idempotency_key, request, execute)

    def evaluate_claim(self, *, idempotency_key: str | None = None, **kwargs: Any) -> dict[str, Any]:
        request = dict(kwargs)

        def execute() -> dict[str, Any]:
            response = super(PersistentThalosMcpRuntime, self).evaluate_claim(**kwargs)
            evaluation = EvidenceEvaluation.model_validate(response)
            self.store.put_record("evaluation", evaluation.evaluation_id, response)
            return response

        return self._idempotent("claim.evaluate", idempotency_key, request, execute)

    def commit_belief(
        self,
        *,
        expected_ledger_version: int,
        approval_receipt: str,
        idempotency_key: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Commit a belief with concurrency, approval, and idempotency controls."""
        if not approval_receipt.strip():
            raise ValueError("approval_receipt is required for belief commitment")
        current = self.store.stream_version()
        if current != expected_ledger_version:
            from thalos_prime.persistence.sqlite_store import OptimisticConcurrencyError

            raise OptimisticConcurrencyError(
                f"expected ledger version {expected_ledger_version}, current version is {current}"
            )
        request = {
            **kwargs,
            "expected_ledger_version": expected_ledger_version,
            "approval_receipt": approval_receipt,
        }

        def execute() -> dict[str, Any]:
            response = super(PersistentThalosMcpRuntime, self).commit_belief(**kwargs)
            self._persist_new_events(current)
            return {
                **response,
                "approval_receipt": approval_receipt,
                "ledger_version": self.store.stream_version(),
            }

        return self._idempotent("belief.commit", idempotency_key, request, execute)

    def export_proof(self, *, idempotency_key: str | None = None, **kwargs: Any) -> dict[str, Any]:
        request = dict(kwargs)

        def execute() -> dict[str, Any]:
            response = super(PersistentThalosMcpRuntime, self).export_proof(**kwargs)
            bundle = ProofBundle.model_validate(response)
            self.store.put_record("proof_bundle", bundle.bundle_id, response)
            return response

        return self._idempotent("proof.export", idempotency_key, request, execute)


__all__ = ["PersistentThalosMcpRuntime"]
