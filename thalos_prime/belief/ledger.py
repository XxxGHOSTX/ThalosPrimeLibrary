"""Belief Base (B_t) - Epistemic ledger for ThalosPrime Library.

Control Plane module: manages the epistemic state of the system, tracking
artifacts across acceptance states (accepted/pending/disputed/rejected).
All operations are atomic and deterministic. Rejected and disputed artifacts
are retained for audit.

State is serializable and versioned for checkpoint/restore.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from thalos_prime.artifacts.schema import Artifact

logger = logging.getLogger(__name__)


class BeliefState(StrEnum):
    """Epistemic acceptance state of an artifact in the Belief Base.

    Members:
        ACCEPTED: Artifact is fully accepted into the knowledge base.
        PENDING: Artifact is awaiting validation.
        DISPUTED: Artifact content is under active dispute.
        REJECTED: Artifact has been formally rejected; retained for audit.

    """

    ACCEPTED = "accepted"
    PENDING = "pending"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class BeliefRecord(BaseModel):
    """A single entry in the epistemic ledger.

    Tracks the acceptance state, confidence, coordinate, lineage, and FACS
    flags for one artifact.

    Attributes:
        artifact_id: Unique identifier of the tracked artifact.
        state: Current epistemic acceptance state.
        confidence: Confidence score in ``[0.0, 1.0]``.
        coordinate_hex: 16-character hex string of the identity coordinate.
        admitted_at_ns: Nanosecond timestamp when first admitted.
        updated_at_ns: Nanosecond timestamp of the last state change.
        lineage: Ordered list of parent artifact IDs.
        version: Artifact revision number carried from the source artifact.
        facs_flags: Named boolean flags from the artifact FACS bundle.

    """

    artifact_id: str
    state: BeliefState
    confidence: float
    coordinate_hex: str
    admitted_at_ns: int
    updated_at_ns: int
    lineage: list[str] = Field(default_factory=list)
    version: int
    facs_flags: dict[str, bool] = Field(default_factory=dict)


class BeliefLedger:
    """Epistemic ledger that tracks artifacts across belief states.

    All records are retained indefinitely; disputed and rejected artifacts
    remain in the ledger for audit. Transitions are strictly validated:
    only ``PENDING`` artifacts may move to ``ACCEPTED``, and any state may
    transition to ``DISPUTED`` or ``REJECTED``.

    This class implements the six-method lifecycle contract so that it
    integrates cleanly with ThalosPrime's lifecycle validation tooling.
    """

    schema_version: ClassVar[int] = 1

    def __init__(self, ledger_id: str) -> None:
        """Initialise an empty epistemic ledger.

        Args:
            ledger_id: Deterministic string identifier for this ledger instance.

        """
        self._ledger_id = ledger_id
        self._records: dict[str, BeliefRecord] = {}
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle protocol
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialise the ledger, resetting all in-memory state.

        Idempotent; calling this on an already-initialised ledger clears
        all existing records.
        """
        self._records = {}
        self._initialized = True
        logger.debug("BeliefLedger(%s) initialised", self._ledger_id)

    def validate(self) -> bool:
        """Validate that the ledger is in a consistent, ready state.

        Returns:
            ``True`` if the ledger is initialised and ready, ``False`` otherwise.

        """
        return self._initialized

    def operate(self) -> None:
        """Log current ledger statistics. Idempotent."""
        logger.debug(
            "BeliefLedger(%s) records=%d",
            self._ledger_id,
            len(self._records),
        )

    def reconcile(self) -> None:
        """Reconcile any inconsistent internal state.

        Currently a no-op; retained for lifecycle protocol compliance.
        """
        logger.debug("BeliefLedger(%s) reconcile called", self._ledger_id)

    def terminate(self) -> None:
        """Terminate the ledger, clearing all in-memory state."""
        self._records = {}
        self._initialized = False
        logger.debug("BeliefLedger(%s) terminated", self._ledger_id)

    # ------------------------------------------------------------------
    # Core epistemic operations
    # ------------------------------------------------------------------

    def admit(
        self,
        artifact: Artifact,
        coordinate_hex: str,
        confidence: float,
        timestamp_ns: int,
    ) -> BeliefRecord:
        """Admit an artifact into the ledger as ``PENDING``.

        Args:
            artifact: The artifact to admit. Its ``artifact_id`` must be unique
                within this ledger.
            coordinate_hex: 16-character hex string of the identity coordinate.
            confidence: Initial confidence score in ``[0.0, 1.0]``.
            timestamp_ns: Nanosecond timestamp for ``admitted_at_ns``.

        Returns:
            The newly created :class:`BeliefRecord`.

        Raises:
            ValueError: When the artifact's ``artifact_id`` is already tracked
                by this ledger.

        """
        if artifact.artifact_id in self._records:
            msg = f"artifact_id already exists: {artifact.artifact_id!r}"
            raise ValueError(msg)
        lineage: list[str] = (
            list(artifact.provenance.parent_ids) if artifact.provenance else []
        )
        facs_flags: dict[str, bool] = (
            dict(artifact.facs.flags) if artifact.facs else {}
        )
        record = BeliefRecord(
            artifact_id=artifact.artifact_id,
            state=BeliefState.PENDING,
            confidence=confidence,
            coordinate_hex=coordinate_hex,
            admitted_at_ns=timestamp_ns,
            updated_at_ns=timestamp_ns,
            lineage=lineage,
            version=artifact.version,
            facs_flags=facs_flags,
        )
        self._records[artifact.artifact_id] = record
        logger.debug(
            "BeliefLedger(%s) admitted artifact_id=%r",
            self._ledger_id,
            artifact.artifact_id,
        )
        return record

    def accept(self, artifact_id: str, timestamp_ns: int) -> BeliefRecord:
        """Transition a ``PENDING`` artifact to ``ACCEPTED``.

        Args:
            artifact_id: ID of the artifact to accept.
            timestamp_ns: Nanosecond timestamp for ``updated_at_ns``.

        Returns:
            The updated :class:`BeliefRecord`.

        Raises:
            KeyError: When *artifact_id* is not tracked by this ledger.
            ValueError: When the artifact is not in ``PENDING`` state.

        """
        if artifact_id not in self._records:
            raise KeyError(artifact_id)
        record = self._records[artifact_id]
        if record.state is not BeliefState.PENDING:
            msg = f"artifact must be PENDING to accept; current state: {record.state.value!r}"
            raise ValueError(msg)
        updated = record.model_copy(
            update={"state": BeliefState.ACCEPTED, "updated_at_ns": timestamp_ns}
        )
        self._records[artifact_id] = updated
        return updated

    def dispute(self, artifact_id: str, reason: str, timestamp_ns: int) -> BeliefRecord:
        """Transition an artifact to ``DISPUTED`` and set the ``disputed`` FACS flag.

        Args:
            artifact_id: ID of the artifact to dispute.
            reason: Human-readable reason string (recorded in debug log).
            timestamp_ns: Nanosecond timestamp for ``updated_at_ns``.

        Returns:
            The updated :class:`BeliefRecord`.

        Raises:
            KeyError: When *artifact_id* is not tracked by this ledger.

        """
        if artifact_id not in self._records:
            raise KeyError(artifact_id)
        record = self._records[artifact_id]
        new_flags = {**record.facs_flags, "disputed": True}
        updated = record.model_copy(
            update={
                "state": BeliefState.DISPUTED,
                "updated_at_ns": timestamp_ns,
                "facs_flags": new_flags,
            }
        )
        self._records[artifact_id] = updated
        logger.debug(
            "BeliefLedger(%s) disputed artifact_id=%r reason=%r",
            self._ledger_id,
            artifact_id,
            reason,
        )
        return updated

    def reject(self, artifact_id: str, reason: str, timestamp_ns: int) -> BeliefRecord:
        """Transition an artifact to ``REJECTED`` and set the ``rejected`` FACS flag.

        Args:
            artifact_id: ID of the artifact to reject.
            reason: Human-readable reason string (recorded in debug log).
            timestamp_ns: Nanosecond timestamp for ``updated_at_ns``.

        Returns:
            The updated :class:`BeliefRecord`.

        Raises:
            KeyError: When *artifact_id* is not tracked by this ledger.

        """
        if artifact_id not in self._records:
            raise KeyError(artifact_id)
        record = self._records[artifact_id]
        new_flags = {**record.facs_flags, "rejected": True}
        updated = record.model_copy(
            update={
                "state": BeliefState.REJECTED,
                "updated_at_ns": timestamp_ns,
                "facs_flags": new_flags,
            }
        )
        self._records[artifact_id] = updated
        logger.debug(
            "BeliefLedger(%s) rejected artifact_id=%r reason=%r",
            self._ledger_id,
            artifact_id,
            reason,
        )
        return updated

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    def query_by_confidence(
        self,
        min_confidence: float,
        state: BeliefState | None = None,
    ) -> list[BeliefRecord]:
        """Return records whose confidence is at or above *min_confidence*.

        Args:
            min_confidence: Minimum confidence threshold (inclusive).
            state: If provided, further restrict results to this belief state.

        Returns:
            Sorted list of matching :class:`BeliefRecord` instances, ordered
            by ``artifact_id`` for determinism.

        """
        results = [
            r
            for r in self._records.values()
            if r.confidence >= min_confidence and (state is None or r.state is state)
        ]
        return sorted(results, key=lambda r: r.artifact_id)

    def resolve_by_coordinate(self, coordinate_hex: str) -> BeliefRecord | None:
        """Find the first record whose ``coordinate_hex`` matches.

        Args:
            coordinate_hex: 16-character hex coordinate string to look up.

        Returns:
            The matching :class:`BeliefRecord`, or ``None`` if not found.

        """
        for record in self._records.values():
            if record.coordinate_hex == coordinate_hex:
                return record
        return None

    def get_lineage(self, artifact_id: str) -> list[BeliefRecord]:
        """Recursively collect all ancestor records of *artifact_id*.

        Traverses the ``lineage`` lists of each ancestor, deduplicating by
        ``artifact_id`` and retaining insertion order.

        Args:
            artifact_id: Starting artifact ID whose ancestors are collected.

        Returns:
            Ordered list of ancestor :class:`BeliefRecord` instances, with
            the most immediate parents first and cycles prevented.

        """
        root = self._records.get(artifact_id)
        if root is None:
            return []
        visited: set[str] = {artifact_id}
        result: list[BeliefRecord] = []
        queue: list[str] = list(root.lineage)
        while queue:
            parent_id = queue.pop(0)
            if parent_id in visited:
                continue
            visited.add(parent_id)
            parent = self._records.get(parent_id)
            if parent is not None:
                result.append(parent)
                queue.extend(parent.lineage)
        return result

    def get_by_state(self, state: BeliefState) -> list[BeliefRecord]:
        """Return all records in a given belief state.

        Args:
            state: The :class:`BeliefState` to filter by.

        Returns:
            Sorted list of :class:`BeliefRecord` instances in *state*,
            ordered by ``artifact_id`` for determinism.

        """
        return sorted(
            (r for r in self._records.values() if r.state is state),
            key=lambda r: r.artifact_id,
        )

    # ------------------------------------------------------------------
    # Checkpoint / restore
    # ------------------------------------------------------------------

    def checkpoint(self) -> dict[str, object]:
        """Serialize the full ledger state for checkpoint/restore.

        Returns:
            A dictionary containing ``ledger_id``, ``schema_version``, and
            a ``records`` sub-dict mapping ``artifact_id`` → serialized record.

        """
        return {
            "ledger_id": self._ledger_id,
            "schema_version": self.schema_version,
            "records": {
                aid: record.model_dump()
                for aid, record in self._records.items()
            },
        }

    def restore(self, data: dict[str, object]) -> None:
        """Restore ledger state from a checkpoint dictionary.

        Args:
            data: A dictionary previously produced by :meth:`checkpoint`.

        Raises:
            ValueError: When the ``schema_version`` in *data* does not match
                :attr:`schema_version`, or when ``records`` has an unexpected type.

        """
        incoming_version = data.get("schema_version")
        if incoming_version != self.schema_version:
            msg = f"unsupported schema_version: {incoming_version!r}"
            raise ValueError(msg)
        records_raw = data.get("records", {})
        if not isinstance(records_raw, dict):
            msg = "checkpoint 'records' must be a dict"
            raise TypeError(msg)
        new_records: dict[str, BeliefRecord] = {}
        for artifact_id, record_data in records_raw.items():
            if isinstance(record_data, dict):
                new_records[str(artifact_id)] = BeliefRecord.model_validate(record_data)
        ledger_id_raw = data.get("ledger_id")
        if isinstance(ledger_id_raw, str):
            self._ledger_id = ledger_id_raw
        self._records = new_records
        self._initialized = True
        logger.debug(
            "BeliefLedger(%s) restored %d records",
            self._ledger_id,
            len(self._records),
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def ledger_id(self) -> str:
        """Deterministic string identifier for this ledger instance."""
        return self._ledger_id


__all__ = [
    "BeliefLedger",
    "BeliefRecord",
    "BeliefState",
]
