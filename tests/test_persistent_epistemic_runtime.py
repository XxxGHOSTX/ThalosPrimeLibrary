"""Persistence and restart tests for the Thalos Prime MCP runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

from thalos_prime.persistence import (
    IdempotencyConflict,
    OptimisticConcurrencyError,
    PersistentThalosMcpRuntime,
)


def _prepare_runtime(database: Path) -> tuple[PersistentThalosMcpRuntime, dict[str, str]]:
    runtime = PersistentThalosMcpRuntime(database)
    artifact = runtime.ingest_artifact(
        text="Thalos Prime stores evidence and belief transitions deterministically.",
        trust_class="primary",
        idempotency_key="artifact-1",
    )
    snapshot = runtime.create_snapshot(
        artifact_ids=[artifact["artifact_id"]],
        created_by_run="bootstrap",
        idempotency_key="snapshot-1",
    )
    run = runtime.create_run(
        query="Does Thalos Prime store belief transitions deterministically?",
        snapshot_id=snapshot["snapshot_id"],
        code_commit="test",
        dependency_lock_hash="test",
        idempotency_key="run-1",
    )
    claim = runtime.register_claim(
        text="Thalos Prime stores belief transitions deterministically.",
        run_id=run["run_id"],
        idempotency_key="claim-1",
    )
    evidence = runtime.bind_evidence(
        artifact_id=artifact["artifact_id"],
        start=0,
        end=len(artifact["canonical_text"]),
        idempotency_key="evidence-1",
    )
    evaluation = runtime.evaluate_claim(
        claim_id=claim["claim_id"],
        supporting_evidence=[evidence["evidence_id"]],
        entailment=0.95,
        temporal_validity=1.0,
        scope_validity=1.0,
        source_independence=0.8,
        idempotency_key="evaluation-1",
    )
    return runtime, {
        "artifact_id": artifact["artifact_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "run_id": run["run_id"],
        "claim_id": claim["claim_id"],
        "evidence_id": evidence["evidence_id"],
        "evaluation_id": evaluation["evaluation_id"],
    }


def test_runtime_survives_restart(tmp_path: Path) -> None:
    database = tmp_path / "thalos.db"
    runtime, ids = _prepare_runtime(database)
    version = runtime.store.stream_version()
    result = runtime.commit_belief(
        claim_id=ids["claim_id"],
        evaluation_id=ids["evaluation_id"],
        run_id=ids["run_id"],
        expected_ledger_version=version,
        approval_receipt="approval:test",
        idempotency_key="commit-1",
    )
    assert result["state"] == "accepted"
    runtime.close()

    restored = PersistentThalosMcpRuntime(database)
    belief = restored.get_belief(claim_id=ids["claim_id"])
    assert belief["state"] == "accepted"
    assert restored.engine.ledger.event_log.verify()
    assert restored.store.stream_version() == result["ledger_version"]
    restored.close()


def test_idempotent_write_returns_prior_response(tmp_path: Path) -> None:
    runtime = PersistentThalosMcpRuntime(tmp_path / "thalos.db")
    first = runtime.ingest_artifact(
        text="same source",
        idempotency_key="same-key",
    )
    second = runtime.ingest_artifact(
        text="same source",
        idempotency_key="same-key",
    )
    assert first == second
    runtime.close()


def test_idempotency_key_conflict_is_rejected(tmp_path: Path) -> None:
    runtime = PersistentThalosMcpRuntime(tmp_path / "thalos.db")
    runtime.ingest_artifact(text="first", idempotency_key="collision")
    with pytest.raises(IdempotencyConflict):
        runtime.ingest_artifact(text="second", idempotency_key="collision")
    runtime.close()


def test_stale_ledger_version_is_rejected(tmp_path: Path) -> None:
    runtime, ids = _prepare_runtime(tmp_path / "thalos.db")
    with pytest.raises(OptimisticConcurrencyError):
        runtime.commit_belief(
            claim_id=ids["claim_id"],
            evaluation_id=ids["evaluation_id"],
            run_id=ids["run_id"],
            expected_ledger_version=0,
            approval_receipt="approval:test",
            idempotency_key="commit-stale",
        )
    runtime.close()


def test_commit_requires_approval_receipt(tmp_path: Path) -> None:
    runtime, ids = _prepare_runtime(tmp_path / "thalos.db")
    with pytest.raises(ValueError, match="approval_receipt"):
        runtime.commit_belief(
            claim_id=ids["claim_id"],
            evaluation_id=ids["evaluation_id"],
            run_id=ids["run_id"],
            expected_ledger_version=runtime.store.stream_version(),
            approval_receipt="",
            idempotency_key="commit-no-approval",
        )
    runtime.close()
