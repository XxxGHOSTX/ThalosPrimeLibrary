"""Tests for the Belief Base (B_t) epistemic ledger subsystem.

Covers BeliefState, BeliefRecord, and BeliefLedger including happy path,
state transitions, validation, serialisation, and lineage traversal.
All tests use deterministic inputs and fixed timestamps.
"""

from __future__ import annotations

import pytest

from thalos_prime.artifacts.schema import Artifact, FacsBundle, ProvenanceNode
from thalos_prime.belief.ledger import BeliefLedger, BeliefRecord, BeliefState

# ---------------------------------------------------------------------------
# Fixed test constants
# ---------------------------------------------------------------------------
_TS = 1_700_000_000_000_000_000  # Fixed nanosecond timestamp
_TS2 = _TS + 1_000_000_000      # One second later
_COORD = "0001020300040005"       # 16-char coordinate hex


def _make_artifact(content: str = "test content", ts: int = _TS) -> Artifact:
    """Create a deterministic test artifact."""
    return Artifact.create(content=content, source_uris=["uri://test"], timestamp_ns=ts)


def _make_ledger(ledger_id: str = "ledger-001") -> BeliefLedger:
    """Create and initialise a fresh test ledger."""
    ledger = BeliefLedger(ledger_id=ledger_id)
    ledger.initialize()
    return ledger


# ===========================================================================
# BeliefState
# ===========================================================================


class TestBeliefState:
    def test_all_members(self) -> None:
        members = set(BeliefState)
        assert BeliefState.ACCEPTED in members
        assert BeliefState.PENDING in members
        assert BeliefState.DISPUTED in members
        assert BeliefState.REJECTED in members

    def test_string_values(self) -> None:
        assert BeliefState.ACCEPTED.value == "accepted"
        assert BeliefState.PENDING.value == "pending"
        assert BeliefState.DISPUTED.value == "disputed"
        assert BeliefState.REJECTED.value == "rejected"

    def test_is_str(self) -> None:
        assert isinstance(BeliefState.PENDING, str)


# ===========================================================================
# BeliefRecord
# ===========================================================================


class TestBeliefRecord:
    def test_defaults(self) -> None:
        record = BeliefRecord(
            artifact_id="a1",
            state=BeliefState.PENDING,
            confidence=0.5,
            coordinate_hex=_COORD,
            admitted_at_ns=_TS,
            updated_at_ns=_TS,
            version=1,
        )
        assert record.lineage == []
        assert record.facs_flags == {}

    def test_fields_populated(self) -> None:
        record = BeliefRecord(
            artifact_id="a2",
            state=BeliefState.ACCEPTED,
            confidence=0.9,
            coordinate_hex=_COORD,
            admitted_at_ns=_TS,
            updated_at_ns=_TS2,
            lineage=["parent-1"],
            version=2,
            facs_flags={"verified": True},
        )
        assert record.artifact_id == "a2"
        assert record.state is BeliefState.ACCEPTED
        assert record.confidence == 0.9
        assert record.lineage == ["parent-1"]
        assert record.facs_flags["verified"] is True

    def test_serialisation_round_trip(self) -> None:
        record = BeliefRecord(
            artifact_id="rt",
            state=BeliefState.DISPUTED,
            confidence=0.3,
            coordinate_hex=_COORD,
            admitted_at_ns=_TS,
            updated_at_ns=_TS,
            version=1,
        )
        data = record.model_dump()
        restored = BeliefRecord.model_validate(data)
        assert restored == record


# ===========================================================================
# BeliefLedger - lifecycle
# ===========================================================================


class TestBeliefLedgerLifecycle:
    def test_initialize_sets_initialized(self) -> None:
        ledger = BeliefLedger(ledger_id="lc-1")
        ledger.initialize()
        assert ledger.validate() is True

    def test_validate_before_initialize(self) -> None:
        ledger = BeliefLedger(ledger_id="lc-2")
        assert ledger.validate() is False

    def test_initialize_clears_records(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.5, _TS)
        assert len(ledger.get_by_state(BeliefState.PENDING)) == 1
        ledger.initialize()
        assert len(ledger.get_by_state(BeliefState.PENDING)) == 0

    def test_terminate_clears_state(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.5, _TS)
        ledger.terminate()
        assert ledger.validate() is False

    def test_operate_does_not_raise(self) -> None:
        ledger = _make_ledger()
        ledger.operate()

    def test_reconcile_does_not_raise(self) -> None:
        ledger = _make_ledger()
        ledger.reconcile()

    def test_ledger_id_property(self) -> None:
        ledger = BeliefLedger(ledger_id="my-ledger")
        assert ledger.ledger_id == "my-ledger"

    def test_schema_version_class_attribute(self) -> None:
        assert BeliefLedger.schema_version == 1


# ===========================================================================
# BeliefLedger - admit
# ===========================================================================


class TestBeliefLedgerAdmit:
    def test_admit_creates_pending_record(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        record = ledger.admit(artifact, _COORD, 0.6, _TS)
        assert record.state is BeliefState.PENDING
        assert record.artifact_id == artifact.artifact_id
        assert record.confidence == 0.6
        assert record.coordinate_hex == _COORD
        assert record.admitted_at_ns == _TS

    def test_admit_duplicate_raises(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.5, _TS)
        with pytest.raises(ValueError, match="already exists"):
            ledger.admit(artifact, _COORD, 0.5, _TS)

    def test_admit_extracts_lineage_from_provenance(self) -> None:
        artifact = _make_artifact()
        prov = ProvenanceNode(
            node_id="n1",
            artifact_id=artifact.artifact_id,
            parent_ids=["parent-a", "parent-b"],
            derivation_steps=[],
            created_at_ns=_TS,
            version=1,
        )
        artifact_with_prov = artifact.model_copy(update={"provenance": prov})
        ledger = _make_ledger()
        record = ledger.admit(artifact_with_prov, _COORD, 0.5, _TS)
        assert record.lineage == ["parent-a", "parent-b"]

    def test_admit_extracts_facs_flags(self) -> None:
        artifact = _make_artifact()
        facs = FacsBundle(flags={"verified": True, "disputed": False})
        artifact_with_facs = artifact.model_copy(update={"facs": facs})
        ledger = _make_ledger()
        record = ledger.admit(artifact_with_facs, _COORD, 0.5, _TS)
        assert record.facs_flags["verified"] is True

    def test_admit_multiple_artifacts(self) -> None:
        ledger = _make_ledger()
        a1 = _make_artifact("content one")
        a2 = _make_artifact("content two")
        ledger.admit(a1, _COORD, 0.5, _TS)
        ledger.admit(a2, _COORD, 0.7, _TS)
        assert len(ledger.get_by_state(BeliefState.PENDING)) == 2


# ===========================================================================
# BeliefLedger - accept
# ===========================================================================


class TestBeliefLedgerAccept:
    def test_accept_pending_to_accepted(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.8, _TS)
        record = ledger.accept(artifact.artifact_id, _TS2)
        assert record.state is BeliefState.ACCEPTED
        assert record.updated_at_ns == _TS2

    def test_accept_unknown_artifact_raises_key_error(self) -> None:
        ledger = _make_ledger()
        with pytest.raises(KeyError):
            ledger.accept("does-not-exist", _TS)

    def test_accept_non_pending_raises_value_error(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.5, _TS)
        ledger.accept(artifact.artifact_id, _TS2)
        with pytest.raises(ValueError, match="PENDING"):
            ledger.accept(artifact.artifact_id, _TS2)

    def test_accept_updates_state_in_store(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.7, _TS)
        ledger.accept(artifact.artifact_id, _TS2)
        accepted = ledger.get_by_state(BeliefState.ACCEPTED)
        assert len(accepted) == 1
        assert accepted[0].artifact_id == artifact.artifact_id


# ===========================================================================
# BeliefLedger - dispute
# ===========================================================================


class TestBeliefLedgerDispute:
    def test_dispute_sets_disputed_flag(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.5, _TS)
        record = ledger.dispute(artifact.artifact_id, "conflicting data", _TS2)
        assert record.state is BeliefState.DISPUTED
        assert record.facs_flags["disputed"] is True
        assert record.updated_at_ns == _TS2

    def test_dispute_unknown_raises_key_error(self) -> None:
        ledger = _make_ledger()
        with pytest.raises(KeyError):
            ledger.dispute("no-such-id", "reason", _TS)

    def test_dispute_accepted_artifact(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.5, _TS)
        ledger.accept(artifact.artifact_id, _TS2)
        record = ledger.dispute(artifact.artifact_id, "new evidence", _TS2)
        assert record.state is BeliefState.DISPUTED

    def test_dispute_preserves_existing_flags(self) -> None:
        artifact = _make_artifact()
        facs = FacsBundle(flags={"verified": True})
        artifact_with_facs = artifact.model_copy(update={"facs": facs})
        ledger = _make_ledger()
        ledger.admit(artifact_with_facs, _COORD, 0.5, _TS)
        record = ledger.dispute(artifact_with_facs.artifact_id, "r", _TS2)
        assert record.facs_flags["verified"] is True
        assert record.facs_flags["disputed"] is True


# ===========================================================================
# BeliefLedger - reject
# ===========================================================================


class TestBeliefLedgerReject:
    def test_reject_sets_rejected_flag(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.5, _TS)
        record = ledger.reject(artifact.artifact_id, "invalid source", _TS2)
        assert record.state is BeliefState.REJECTED
        assert record.facs_flags["rejected"] is True
        assert record.updated_at_ns == _TS2

    def test_reject_unknown_raises_key_error(self) -> None:
        ledger = _make_ledger()
        with pytest.raises(KeyError):
            ledger.reject("unknown", "bad data", _TS)

    def test_rejected_artifact_retained_for_audit(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.5, _TS)
        ledger.reject(artifact.artifact_id, "audit", _TS2)
        rejected = ledger.get_by_state(BeliefState.REJECTED)
        assert len(rejected) == 1


# ===========================================================================
# BeliefLedger - query operations
# ===========================================================================


class TestBeliefLedgerQuery:
    def test_query_by_confidence_min(self) -> None:
        ledger = _make_ledger()
        a1 = _make_artifact("c1")
        a2 = _make_artifact("c2")
        ledger.admit(a1, _COORD, 0.3, _TS)
        ledger.admit(a2, _COORD, 0.8, _TS)
        results = ledger.query_by_confidence(0.5)
        assert len(results) == 1
        assert results[0].artifact_id == a2.artifact_id

    def test_query_by_confidence_and_state(self) -> None:
        ledger = _make_ledger()
        a1 = _make_artifact("cq1")
        a2 = _make_artifact("cq2")
        ledger.admit(a1, _COORD, 0.9, _TS)
        ledger.admit(a2, _COORD, 0.9, _TS)
        ledger.accept(a1.artifact_id, _TS2)
        results = ledger.query_by_confidence(0.5, state=BeliefState.ACCEPTED)
        assert len(results) == 1
        assert results[0].artifact_id == a1.artifact_id

    def test_query_by_confidence_sorted_by_artifact_id(self) -> None:
        ledger = _make_ledger()
        artifacts = [_make_artifact(f"content-{i}") for i in range(3)]
        for a in artifacts:
            ledger.admit(a, _COORD, 1.0, _TS)
        results = ledger.query_by_confidence(0.0)
        ids = [r.artifact_id for r in results]
        assert ids == sorted(ids)

    def test_resolve_by_coordinate_found(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.5, _TS)
        result = ledger.resolve_by_coordinate(_COORD)
        assert result is not None
        assert result.artifact_id == artifact.artifact_id

    def test_resolve_by_coordinate_not_found(self) -> None:
        ledger = _make_ledger()
        result = ledger.resolve_by_coordinate("ffffffffffffffff")
        assert result is None

    def test_get_by_state_pending(self) -> None:
        ledger = _make_ledger()
        a1 = _make_artifact("pending-1")
        a2 = _make_artifact("pending-2")
        ledger.admit(a1, _COORD, 0.5, _TS)
        ledger.admit(a2, _COORD, 0.6, _TS)
        ledger.accept(a1.artifact_id, _TS2)
        pending = ledger.get_by_state(BeliefState.PENDING)
        assert len(pending) == 1
        assert pending[0].artifact_id == a2.artifact_id

    def test_get_by_state_empty(self) -> None:
        ledger = _make_ledger()
        assert ledger.get_by_state(BeliefState.ACCEPTED) == []


# ===========================================================================
# BeliefLedger - lineage
# ===========================================================================


class TestBeliefLedgerLineage:
    def test_get_lineage_no_parents(self) -> None:
        ledger = _make_ledger()
        artifact = _make_artifact()
        ledger.admit(artifact, _COORD, 0.5, _TS)
        lineage = ledger.get_lineage(artifact.artifact_id)
        assert lineage == []

    def test_get_lineage_with_parent(self) -> None:
        ledger = _make_ledger()
        parent = _make_artifact("parent")
        ledger.admit(parent, _COORD, 0.8, _TS)

        child_artifact = _make_artifact("child")
        prov = ProvenanceNode(
            node_id="n-child",
            artifact_id=child_artifact.artifact_id,
            parent_ids=[parent.artifact_id],
            derivation_steps=[],
            created_at_ns=_TS,
            version=1,
        )
        child_with_prov = child_artifact.model_copy(update={"provenance": prov})
        ledger.admit(child_with_prov, _COORD, 0.7, _TS)

        lineage = ledger.get_lineage(child_with_prov.artifact_id)
        assert len(lineage) == 1
        assert lineage[0].artifact_id == parent.artifact_id

    def test_get_lineage_missing_parent_skipped(self) -> None:
        """Lineage references to non-admitted artifacts are silently skipped."""
        ledger = _make_ledger()
        child_artifact = _make_artifact("orphan-child")
        prov = ProvenanceNode(
            node_id="n-orphan",
            artifact_id=child_artifact.artifact_id,
            parent_ids=["missing-parent-id"],
            derivation_steps=[],
            created_at_ns=_TS,
            version=1,
        )
        child_with_prov = child_artifact.model_copy(update={"provenance": prov})
        ledger.admit(child_with_prov, _COORD, 0.5, _TS)
        lineage = ledger.get_lineage(child_with_prov.artifact_id)
        assert lineage == []


# ===========================================================================
# BeliefLedger - checkpoint / restore
# ===========================================================================


class TestBeliefLedgerCheckpointRestore:
    def test_checkpoint_contains_required_keys(self) -> None:
        ledger = _make_ledger()
        cp = ledger.checkpoint()
        assert "ledger_id" in cp
        assert "schema_version" in cp
        assert "records" in cp

    def test_checkpoint_schema_version(self) -> None:
        ledger = _make_ledger()
        cp = ledger.checkpoint()
        assert cp["schema_version"] == 1

    def test_checkpoint_ledger_id(self) -> None:
        ledger = BeliefLedger(ledger_id="checkpoint-ledger")
        ledger.initialize()
        cp = ledger.checkpoint()
        assert cp["ledger_id"] == "checkpoint-ledger"

    def test_restore_round_trip(self) -> None:
        ledger = _make_ledger()
        a1 = _make_artifact("cp-artifact-1")
        a2 = _make_artifact("cp-artifact-2")
        ledger.admit(a1, _COORD, 0.5, _TS)
        ledger.admit(a2, _COORD, 0.9, _TS)
        ledger.accept(a1.artifact_id, _TS2)

        cp = ledger.checkpoint()

        new_ledger = BeliefLedger(ledger_id="restored")
        new_ledger.restore(cp)

        restored_pending = new_ledger.get_by_state(BeliefState.PENDING)
        restored_accepted = new_ledger.get_by_state(BeliefState.ACCEPTED)
        assert len(restored_pending) == 1
        assert len(restored_accepted) == 1
        assert new_ledger.ledger_id == "ledger-001"

    def test_restore_wrong_schema_version_raises(self) -> None:
        ledger = _make_ledger()
        cp = ledger.checkpoint()
        bad_cp = {**cp, "schema_version": 99}
        with pytest.raises(ValueError, match="schema_version"):
            ledger.restore(bad_cp)

    def test_restore_wrong_records_type_raises(self) -> None:
        ledger = _make_ledger()
        cp = {**ledger.checkpoint(), "records": "not-a-dict"}
        with pytest.raises(TypeError, match="records"):
            ledger.restore(cp)

    def test_restore_sets_initialized(self) -> None:
        ledger = _make_ledger()
        cp = ledger.checkpoint()
        new_ledger = BeliefLedger(ledger_id="fresh")
        assert new_ledger.validate() is False
        new_ledger.restore(cp)
        assert new_ledger.validate() is True
