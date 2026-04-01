"""Tamper-evident audit trail for ThalosPrime Library.

Control Plane module: provides an append-only structured event log for
state transitions, derivation steps, and lifecycle milestones. Each entry
is chained to the previous via SHA-256 of the prior entry's hash, making
tampering detectable.

Event schema is versioned and backward-compatible.
"""

from __future__ import annotations

import hashlib
import logging
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Version string embedded in every computed entry hash.
_ENTRY_VERSION: str = "1.0"


class AuditEventType(StrEnum):
    """Type codes for structured audit events.

    Members:
        ARTIFACT_ADMITTED: An artifact entered the belief base as PENDING.
        ARTIFACT_ACCEPTED: An artifact transitioned to ACCEPTED.
        ARTIFACT_DISPUTED: An artifact was marked DISPUTED.
        ARTIFACT_REJECTED: An artifact was formally rejected.
        DERIVATION_STEP: A derivation operation was recorded.
        LIFECYCLE_MILESTONE: A subsystem lifecycle transition occurred.
        VALIDATION_COMPLETED: A validation pipeline run finished.
        SECURITY_EVENT: A security-relevant action was performed.

    """

    ARTIFACT_ADMITTED = "artifact_admitted"
    ARTIFACT_ACCEPTED = "artifact_accepted"
    ARTIFACT_DISPUTED = "artifact_disputed"
    ARTIFACT_REJECTED = "artifact_rejected"
    DERIVATION_STEP = "derivation_step"
    LIFECYCLE_MILESTONE = "lifecycle_milestone"
    VALIDATION_COMPLETED = "validation_completed"
    SECURITY_EVENT = "security_event"


class AuditEvent(BaseModel):
    """A single entry in the append-only audit trail.

    The ``entry_hash`` and ``prev_hash`` form a SHA-256 chain; any tampering
    at position *i* invalidates all subsequent hashes.

    Attributes:
        event_id: SHA-256 digest of the concatenated prev_hash, event_type
            value, artifact_id (or empty string), and timestamp_ns string.
        event_type: Categorises the event.
        artifact_id: ID of the artifact involved, if applicable.
        timestamp_ns: Nanosecond-precision event timestamp.
        seed: Randomness seed used, if any.
        config_hash: SHA-256 of the relevant configuration, if applicable.
        version: Schema version string for this event.
        schema_version: Integer schema version for forward-compatibility.
        payload: Event-specific key/value data.
        prev_hash: ``entry_hash`` of the preceding event, or ``""`` for the
            first event.
        entry_hash: SHA-256(prev_hash + event_type + artifact_id + timestamp_ns
            + version), computed at creation.

    """

    event_id: str
    event_type: AuditEventType
    artifact_id: str | None = None
    timestamp_ns: int
    seed: str | None = None
    config_hash: str | None = None
    version: str = Field(default=_ENTRY_VERSION)
    schema_version: int = 1
    payload: dict[str, str] = Field(default_factory=dict)
    prev_hash: str
    entry_hash: str


class AuditTrail:
    """Append-only, SHA-256-chained audit trail.

    Every event appended to the trail is linked to its predecessor via the
    ``prev_hash`` / ``entry_hash`` chain.  Calling :meth:`verify_integrity`
    re-derives all hashes and confirms the chain is intact.

    This class implements the six-method lifecycle contract required by the
    ThalosPrime lifecycle validator.
    """

    schema_version: ClassVar[int] = 1

    def __init__(self, trail_id: str) -> None:
        """Initialise an empty audit trail.

        Args:
            trail_id: Deterministic string identifier for this trail instance.

        """
        self._trail_id = trail_id
        self._events: list[AuditEvent] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def trail_id(self) -> str:
        """Deterministic string identifier for this trail instance.

        Returns:
            The trail ID supplied at construction time.

        """
        return self._trail_id

    @property
    def event_count(self) -> int:
        """Number of events currently stored in the trail.

        Returns:
            Integer count of appended events.

        """
        return len(self._events)

    @property
    def head_hash(self) -> str:
        """Entry hash of the most recently appended event.

        Returns:
            The ``entry_hash`` of the last event, or ``""`` when the trail is
            empty.

        """
        return self._events[-1].entry_hash if self._events else ""

    # ------------------------------------------------------------------
    # Hash utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_entry_hash(prev_hash: str, event: AuditEvent) -> str:
        """Re-derive the SHA-256 chain hash for *event*.

        The hash input is the UTF-8 encoding of the concatenation of
        ``prev_hash``, ``event.event_type.value``, ``event.artifact_id``
        (or ``""``), ``str(event.timestamp_ns)``, and ``event.version``.

        Args:
            prev_hash: Entry hash of the preceding event (``""`` for first).
            event: The event whose chain hash is being computed.

        Returns:
            Lowercase 64-character hexadecimal SHA-256 digest.

        """
        raw = (
            prev_hash
            + event.event_type.value
            + (event.artifact_id or "")
            + str(event.timestamp_ns)
            + event.version
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def append(
        self,
        event_type: AuditEventType,
        artifact_id: str | None,
        timestamp_ns: int,
        payload: dict[str, str],
        seed: str | None = None,
        config_hash: str | None = None,
    ) -> AuditEvent:
        """Create and append a new chained audit event.

        The ``event_id`` is the SHA-256 of prev_hash + event_type + artifact_id
        + timestamp_ns (no version suffix, distinct from ``entry_hash``).
        The ``entry_hash`` is the SHA-256 of those same inputs plus the version
        string, forming the chain link.

        Args:
            event_type: Categorises the event.
            artifact_id: ID of the affected artifact, or ``None``.
            timestamp_ns: Nanosecond-precision event timestamp.
            payload: Event-specific key/value data.
            seed: Randomness seed used during the operation, if any.
            config_hash: SHA-256 of the relevant configuration, if applicable.

        Returns:
            The newly created and appended :class:`AuditEvent`.

        """
        prev_hash = self.head_hash

        # Compute event_id: hash without the version suffix.
        event_id_raw = (
            prev_hash
            + event_type.value
            + (artifact_id or "")
            + str(timestamp_ns)
        ).encode("utf-8")
        event_id = hashlib.sha256(event_id_raw).hexdigest()

        # Compute entry_hash: hash with the version suffix (the chain link).
        entry_hash_raw = (
            prev_hash
            + event_type.value
            + (artifact_id or "")
            + str(timestamp_ns)
            + _ENTRY_VERSION
        ).encode("utf-8")
        entry_hash = hashlib.sha256(entry_hash_raw).hexdigest()

        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            artifact_id=artifact_id,
            timestamp_ns=timestamp_ns,
            seed=seed,
            config_hash=config_hash,
            payload=payload,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        self._events.append(event)
        logger.debug(
            "AuditTrail(%s) appended event_type=%r event_id=%s",
            self._trail_id,
            event_type.value,
            event_id,
        )
        return event

    def verify_integrity(self) -> bool:
        """Verify the SHA-256 chain across all stored events.

        Re-derives each event's ``entry_hash`` from first principles and
        confirms it matches the stored value, and that each ``prev_hash``
        matches the preceding event's ``entry_hash``.

        Returns:
            ``True`` when the entire chain is intact, ``False`` if any
            hash does not match.

        """
        prev_hash = ""
        for event in self._events:
            if event.prev_hash != prev_hash:
                logger.warning(
                    "AuditTrail(%s) prev_hash mismatch at event_id=%s",
                    self._trail_id,
                    event.event_id,
                )
                return False
            expected = AuditTrail._compute_entry_hash(prev_hash, event)
            if event.entry_hash != expected:
                logger.warning(
                    "AuditTrail(%s) entry_hash mismatch at event_id=%s",
                    self._trail_id,
                    event.event_id,
                )
                return False
            prev_hash = event.entry_hash
        return True

    def get_events(
        self,
        event_type: AuditEventType | None = None,
    ) -> list[AuditEvent]:
        """Return all events, optionally filtered by type.

        Args:
            event_type: When provided, only events of this type are returned.
                When ``None``, all events are returned.

        Returns:
            Ordered list of matching :class:`AuditEvent` instances.

        """
        if event_type is None:
            return list(self._events)
        return [e for e in self._events if e.event_type is event_type]

    def get_events_for_artifact(self, artifact_id: str) -> list[AuditEvent]:
        """Return all events whose ``artifact_id`` matches.

        Args:
            artifact_id: The artifact ID to filter by.

        Returns:
            Ordered list of :class:`AuditEvent` instances for *artifact_id*.

        """
        return [e for e in self._events if e.artifact_id == artifact_id]

    # ------------------------------------------------------------------
    # Checkpoint / restore
    # ------------------------------------------------------------------

    def checkpoint(self) -> dict[str, object]:
        """Serialise the full trail for checkpoint/restore.

        Returns:
            A dictionary with ``trail_id``, ``schema_version``, and
            ``events`` (a list of serialised event dictionaries).

        """
        return {
            "trail_id": self._trail_id,
            "schema_version": self.schema_version,
            "events": [event.model_dump() for event in self._events],
        }

    def restore(self, data: dict[str, object]) -> None:
        """Restore trail state from a checkpoint dictionary.

        Args:
            data: A dictionary previously produced by :meth:`checkpoint`.

        Raises:
            ValueError: When the ``schema_version`` is unsupported or chain
                integrity fails after restore.
            TypeError: When ``events`` in *data* is not a list.

        """
        incoming_version = data.get("schema_version")
        if incoming_version != self.schema_version:
            msg = f"unsupported schema_version: {incoming_version!r}"
            raise ValueError(msg)

        events_raw = data.get("events", [])
        if not isinstance(events_raw, list):
            msg = "checkpoint 'events' must be a list"
            raise TypeError(msg)

        trail_id_raw = data.get("trail_id")
        if isinstance(trail_id_raw, str):
            self._trail_id = trail_id_raw

        new_events: list[AuditEvent] = [
            AuditEvent.model_validate(item)
            for item in events_raw
            if isinstance(item, dict)
        ]
        self._events = new_events

        if not self.verify_integrity():
            msg = "restored audit trail has invalid chain integrity"
            raise ValueError(msg)

        logger.debug(
            "AuditTrail(%s) restored %d events",
            self._trail_id,
            len(self._events),
        )

    # ------------------------------------------------------------------
    # Lifecycle protocol
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialise the trail, resetting all in-memory state.

        Idempotent; calling on an existing trail clears all events.
        """
        self._events = []
        logger.debug("AuditTrail(%s) initialised", self._trail_id)

    def validate(self) -> bool:
        """Validate trail integrity.

        Returns:
            ``True`` when the chain is intact (or the trail is empty),
            ``False`` if any hash does not match.

        """
        return self.verify_integrity()

    def operate(
        self,
        event_type: AuditEventType,
        artifact_id: str | None,
        timestamp_ns: int,
        payload: dict[str, str],
        seed: str | None = None,
        config_hash: str | None = None,
    ) -> AuditEvent:
        """Alias for :meth:`append`; satisfies the lifecycle ``operate`` contract.

        Args:
            event_type: Categorises the event.
            artifact_id: ID of the affected artifact, or ``None``.
            timestamp_ns: Nanosecond-precision event timestamp.
            payload: Event-specific key/value data.
            seed: Randomness seed used during the operation, if any.
            config_hash: SHA-256 of relevant configuration, if applicable.

        Returns:
            The newly created and appended :class:`AuditEvent`.

        """
        return self.append(
            event_type=event_type,
            artifact_id=artifact_id,
            timestamp_ns=timestamp_ns,
            payload=payload,
            seed=seed,
            config_hash=config_hash,
        )

    def reconcile(self) -> None:
        """Reconcile trail state.  Currently a no-op; retained for lifecycle compliance."""
        logger.debug("AuditTrail(%s) reconcile called", self._trail_id)

    def terminate(self) -> None:
        """Terminate the trail, clearing all in-memory events."""
        self._events = []
        logger.debug("AuditTrail(%s) terminated", self._trail_id)


__all__ = [
    "AuditEvent",
    "AuditEventType",
    "AuditTrail",
]
