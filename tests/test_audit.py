"""Tests for the tamper-evident AuditTrail subsystem.

Covers AuditEventType, AuditEvent, AuditTrail including happy path,
chain integrity verification, tampering detection, checkpoint/restore,
and lifecycle methods.  All tests use deterministic, fixed timestamps.
"""

from __future__ import annotations

import pytest

from thalos_prime.audit.trail import AuditEvent, AuditEventType, AuditTrail

# ---------------------------------------------------------------------------
# Fixed test constants
# ---------------------------------------------------------------------------
_TS = 1_700_000_000_000_000_000  # Fixed nanosecond timestamp
_TS2 = _TS + 1_000_000_000
_AID = "artifact-abc123"


def _make_trail(trail_id: str = "trail-001") -> AuditTrail:
    trail = AuditTrail(trail_id=trail_id)
    trail.initialize()
    return trail


# ===========================================================================
# AuditEventType
# ===========================================================================


class TestAuditEventType:
    def test_all_members_present(self) -> None:
        members = set(AuditEventType)
        expected = {
            AuditEventType.ARTIFACT_ADMITTED,
            AuditEventType.ARTIFACT_ACCEPTED,
            AuditEventType.ARTIFACT_DISPUTED,
            AuditEventType.ARTIFACT_REJECTED,
            AuditEventType.DERIVATION_STEP,
            AuditEventType.LIFECYCLE_MILESTONE,
            AuditEventType.VALIDATION_COMPLETED,
            AuditEventType.SECURITY_EVENT,
        }
        assert expected.issubset(members)

    def test_is_str(self) -> None:
        assert isinstance(AuditEventType.ARTIFACT_ADMITTED, str)

    def test_values(self) -> None:
        assert AuditEventType.ARTIFACT_ADMITTED.value == "artifact_admitted"
        assert AuditEventType.SECURITY_EVENT.value == "security_event"


# ===========================================================================
# AuditEvent
# ===========================================================================


class TestAuditEvent:
    def test_fields_present(self) -> None:
        event = AuditEvent(
            event_id="e001",
            event_type=AuditEventType.ARTIFACT_ADMITTED,
            artifact_id=_AID,
            timestamp_ns=_TS,
            prev_hash="",
            entry_hash="h001",
        )
        assert event.event_id == "e001"
        assert event.event_type is AuditEventType.ARTIFACT_ADMITTED
        assert event.artifact_id == _AID
        assert event.timestamp_ns == _TS
        assert event.prev_hash == ""
        assert event.entry_hash == "h001"
        assert event.version == "1.0"
        assert event.schema_version == 1

    def test_default_payload_empty(self) -> None:
        event = AuditEvent(
            event_id="e002",
            event_type=AuditEventType.DERIVATION_STEP,
            timestamp_ns=_TS,
            prev_hash="",
            entry_hash="h002",
        )
        assert event.payload == {}
        assert event.artifact_id is None
        assert event.seed is None
        assert event.config_hash is None

    def test_serialisation_round_trip(self) -> None:
        event = AuditEvent(
            event_id="e003",
            event_type=AuditEventType.VALIDATION_COMPLETED,
            artifact_id=_AID,
            timestamp_ns=_TS,
            payload={"status": "accepted"},
            prev_hash="prev",
            entry_hash="entry",
        )
        data = event.model_dump()
        restored = AuditEvent.model_validate(data)
        assert restored == event


# ===========================================================================
# AuditTrail - properties and construction
# ===========================================================================


class TestAuditTrailProperties:
    def test_trail_id(self) -> None:
        trail = _make_trail("my-trail")
        assert trail.trail_id == "my-trail"

    def test_event_count_empty(self) -> None:
        trail = _make_trail()
        assert trail.event_count == 0

    def test_head_hash_empty(self) -> None:
        trail = _make_trail()
        assert trail.head_hash == ""

    def test_event_count_after_append(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        assert trail.event_count == 1

    def test_head_hash_changes_after_append(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        assert trail.head_hash != ""


# ===========================================================================
# AuditTrail - append
# ===========================================================================


class TestAuditTrailAppend:
    def test_first_event_prev_hash_empty(self) -> None:
        trail = _make_trail()
        event = trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        assert event.prev_hash == ""

    def test_second_event_prev_hash_matches_first_entry_hash(self) -> None:
        trail = _make_trail()
        e1 = trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        e2 = trail.append(AuditEventType.ARTIFACT_ACCEPTED, _AID, _TS2, {})
        assert e2.prev_hash == e1.entry_hash

    def test_event_id_is_hex(self) -> None:
        trail = _make_trail()
        event = trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        assert len(event.event_id) == 64
        int(event.event_id, 16)  # Must be valid hex

    def test_entry_hash_is_hex(self) -> None:
        trail = _make_trail()
        event = trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        assert len(event.entry_hash) == 64
        int(event.entry_hash, 16)

    def test_event_id_differs_from_entry_hash(self) -> None:
        trail = _make_trail()
        event = trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        # event_id excludes version; entry_hash includes version
        assert event.event_id != event.entry_hash

    def test_payload_stored(self) -> None:
        trail = _make_trail()
        payload = {"verdict": "accepted", "confidence": "0.95"}
        event = trail.append(AuditEventType.VALIDATION_COMPLETED, _AID, _TS, payload)
        assert event.payload == payload

    def test_seed_stored(self) -> None:
        trail = _make_trail()
        event = trail.append(
            AuditEventType.ARTIFACT_ADMITTED,
            _AID,
            _TS,
            {},
            seed="fixed-seed-42",
        )
        assert event.seed == "fixed-seed-42"

    def test_config_hash_stored(self) -> None:
        trail = _make_trail()
        cfg_hash = "a" * 64
        event = trail.append(
            AuditEventType.SECURITY_EVENT,
            None,
            _TS,
            {},
            config_hash=cfg_hash,
        )
        assert event.config_hash == cfg_hash

    def test_determinism_same_inputs(self) -> None:
        t1 = _make_trail("t1")
        t2 = _make_trail("t2")
        e1 = t1.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {"k": "v"})
        e2 = t2.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {"k": "v"})
        assert e1.event_id == e2.event_id
        assert e1.entry_hash == e2.entry_hash


# ===========================================================================
# AuditTrail - integrity verification
# ===========================================================================


class TestAuditTrailIntegrity:
    def test_empty_trail_is_valid(self) -> None:
        trail = _make_trail()
        assert trail.verify_integrity() is True

    def test_single_event_is_valid(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        assert trail.verify_integrity() is True

    def test_multiple_events_are_valid(self) -> None:
        trail = _make_trail()
        for i in range(5):
            trail.append(
                AuditEventType.ARTIFACT_ADMITTED,
                f"art-{i}",
                _TS + i,
                {},
            )
        assert trail.verify_integrity() is True

    def test_tampered_entry_hash_fails(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        # Tamper the stored entry_hash directly
        original = trail._events[0]
        tampered = original.model_copy(update={"entry_hash": "0" * 64})
        trail._events[0] = tampered
        assert trail.verify_integrity() is False

    def test_tampered_prev_hash_fails(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        trail.append(AuditEventType.ARTIFACT_ACCEPTED, _AID, _TS2, {})
        # Tamper the second event's prev_hash
        original = trail._events[1]
        tampered = original.model_copy(update={"prev_hash": "1" * 64})
        trail._events[1] = tampered
        assert trail.verify_integrity() is False

    def test_validate_lifecycle_method_calls_verify(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        assert trail.validate() is True

    def test_compute_entry_hash_static_method(self) -> None:
        trail = _make_trail()
        event = trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        recomputed = AuditTrail._compute_entry_hash("", event)
        assert recomputed == event.entry_hash


# ===========================================================================
# AuditTrail - get_events / get_events_for_artifact
# ===========================================================================


class TestAuditTrailQuery:
    def test_get_all_events(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        trail.append(AuditEventType.ARTIFACT_ACCEPTED, _AID, _TS2, {})
        events = trail.get_events()
        assert len(events) == 2

    def test_get_events_by_type(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        trail.append(AuditEventType.ARTIFACT_ACCEPTED, _AID, _TS2, {})
        admitted = trail.get_events(AuditEventType.ARTIFACT_ADMITTED)
        assert len(admitted) == 1
        assert admitted[0].event_type is AuditEventType.ARTIFACT_ADMITTED

    def test_get_events_by_type_none_returns_all(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        trail.append(AuditEventType.SECURITY_EVENT, None, _TS2, {})
        all_events = trail.get_events(None)
        assert len(all_events) == 2

    def test_get_events_for_artifact(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, "art-1", _TS, {})
        trail.append(AuditEventType.ARTIFACT_ADMITTED, "art-2", _TS2, {})
        trail.append(AuditEventType.ARTIFACT_ACCEPTED, "art-1", _TS2 + 1, {})
        art1_events = trail.get_events_for_artifact("art-1")
        assert len(art1_events) == 2
        assert all(e.artifact_id == "art-1" for e in art1_events)

    def test_get_events_for_artifact_none_artifact(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.SECURITY_EVENT, None, _TS, {})
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS2, {})
        none_events = trail.get_events_for_artifact("nonexistent")
        assert none_events == []


# ===========================================================================
# AuditTrail - checkpoint / restore
# ===========================================================================


class TestAuditTrailCheckpoint:
    def test_checkpoint_serialises_events(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        data = trail.checkpoint()
        assert "trail_id" in data
        assert "schema_version" in data
        events_raw = data["events"]
        assert isinstance(events_raw, list)
        assert len(events_raw) == 1

    def test_restore_round_trip(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {"k": "v"})
        trail.append(AuditEventType.ARTIFACT_ACCEPTED, _AID, _TS2, {})
        data = trail.checkpoint()

        restored = AuditTrail(trail_id="trail-restored")
        restored.restore(data)

        assert restored.event_count == 2
        assert restored.verify_integrity() is True
        assert restored.trail_id == "trail-001"

    def test_restore_invalid_schema_version_raises(self) -> None:
        trail = _make_trail()
        data: dict[str, object] = {"schema_version": 99, "events": []}
        with pytest.raises(ValueError):
            trail.restore(data)

    def test_restore_invalid_events_type_raises(self) -> None:
        trail = _make_trail()
        data: dict[str, object] = {"schema_version": 1, "events": "not-a-list"}
        with pytest.raises(TypeError):
            trail.restore(data)


# ===========================================================================
# AuditTrail - lifecycle
# ===========================================================================


class TestAuditTrailLifecycle:
    def test_initialize_clears_events(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        trail.initialize()
        assert trail.event_count == 0

    def test_terminate_clears_events(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        trail.terminate()
        assert trail.event_count == 0

    def test_reconcile_is_no_op(self) -> None:
        trail = _make_trail()
        trail.append(AuditEventType.ARTIFACT_ADMITTED, _AID, _TS, {})
        trail.reconcile()
        assert trail.event_count == 1

    def test_operate_alias(self) -> None:
        trail = _make_trail()
        event = trail.operate(
            AuditEventType.ARTIFACT_ADMITTED,
            _AID,
            _TS,
            {"key": "value"},
        )
        assert isinstance(event, AuditEvent)
        assert trail.event_count == 1
