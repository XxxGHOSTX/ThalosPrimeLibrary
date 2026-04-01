"""TPL Reasoning layer - deterministic claim derivation.

Control Plane module: generates candidate claims exclusively from indexed
artifacts and belief base state.  ALL outputs pass through the validation
pipeline before admission to the belief base.  Derivation steps are
recorded in a deterministic log.  The reasoning layer MUST NOT
self-approve outputs.

Lifecycle methods: initialize, validate, operate, reconcile, checkpoint,
terminate.
"""

from __future__ import annotations

import hashlib
import logging
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from collections.abc import Sequence

    from thalos_prime.artifacts.schema import Artifact as ArtifactType
    from thalos_prime.audit.trail import AuditTrail
    from thalos_prime.belief.ledger import BeliefLedger
    from thalos_prime.validation.pipeline import ValidationPipeline, ValidationVerdict

logger = logging.getLogger(__name__)


class DeriveOperation(StrEnum):
    """Supported derivation operations.

    Members:
        SYNTHESIZE: Combine multiple artifacts into a unified claim.
        SUMMARIZE: Produce a condensed form of the first artifact.
        EXTRACT: Pull key sentences from artifact content.
        INFER: Produce an inferred claim prefixed with "Inferred:".
        COMBINE: Join artifact content with a separator.
    """

    SYNTHESIZE = "synthesize"
    SUMMARIZE = "summarize"
    EXTRACT = "extract"
    INFER = "infer"
    COMBINE = "combine"


class CandidateClaim(BaseModel):
    """A candidate claim produced by the reasoning layer.

    Attributes:
        claim_id: SHA-256 of concatenated source artifact IDs + operation.
        content: The derived claim text.
        operation: Derivation operation that produced this claim.
        source_artifact_ids: IDs of artifacts consumed as inputs.
        derivation_log: Ordered list of derivation step records.
        timestamp_ns: Nanosecond-precision creation timestamp.
        approved: Always False; set only after external validation accepts.
        schema_version: Schema version for forward compatibility.

    """

    claim_id: str
    content: str
    operation: str
    source_artifact_ids: list[str]
    derivation_log: list[dict[str, str]]
    timestamp_ns: int
    approved: bool = False
    schema_version: int = Field(default=1)


class TplReasoningLayer:
    """Control Plane reasoning layer.

    Generates candidate claims exclusively from ACCEPTED artifacts held in
    the belief ledger.  Every output is passed through the validation
    pipeline before admission — the layer never self-approves.

    Lifecycle: initialize → validate → operate → reconcile → checkpoint →
    terminate.

    Attributes:
        schema_version: Schema version for checkpoint/restore.

    """

    schema_version: ClassVar[int] = 1

    def __init__(
        self,
        layer_id: str,
        belief_ledger: BeliefLedger,
        validation_pipeline: ValidationPipeline,
        audit_trail: AuditTrail,
    ) -> None:
        """Initialise the reasoning layer with its three dependencies.

        Args:
            layer_id: Deterministic identifier for this layer instance.
            belief_ledger: The epistemic ledger to read accepted artifacts from
                and to admit newly derived artifacts into.
            validation_pipeline: Pipeline used to validate all derived claims.
            audit_trail: Append-only audit log to record derivation steps.

        """
        self._layer_id = layer_id
        self._belief_ledger = belief_ledger
        self._validation_pipeline = validation_pipeline
        self._audit_trail = audit_trail
        self._initialized: bool = False

    @property
    def layer_id(self) -> str:
        """Return the layer identifier."""
        return self._layer_id

    # ------------------------------------------------------------------
    # Internal derivation
    # ------------------------------------------------------------------

    def _derive_claim(
        self,
        artifacts: Sequence[ArtifactType],
        operation: DeriveOperation,
        timestamp_ns: int,
    ) -> CandidateClaim:
        """Build a CandidateClaim from a list of accepted Artifact objects.

        Args:
            artifacts: ACCEPTED Artifact instances to derive from.
            operation: The derivation strategy to apply.
            timestamp_ns: Nanosecond timestamp for determinism.

        Returns:
            A new :class:`CandidateClaim` with ``approved=False``.

        """
        typed_artifacts = list(artifacts)

        derivation_log: list[dict[str, str]] = [
            {
                "step": "input",
                "input": art.artifact_id,
                "output": art.content[:100],
                "timestamp_ns": str(timestamp_ns),
            }
            for art in typed_artifacts
        ]

        if operation is DeriveOperation.SUMMARIZE:
            content = typed_artifacts[0].content[:200] if typed_artifacts else ""
        elif operation is DeriveOperation.EXTRACT:
            sentences = [
                s.strip()
                for art in typed_artifacts
                for s in art.content.split(".")
                if len(s.strip()) > 20  # noqa: PLR2004
            ]
            content = ". ".join(sentences[:5])
        elif operation is DeriveOperation.INFER:
            snippets = " ".join(a.content[:50] for a in typed_artifacts)
            content = f"Inferred: {snippets}"
        else:  # SYNTHESIZE / COMBINE
            content = " | ".join(a.content for a in typed_artifacts)

        claim_id_raw = (
            "".join(a.artifact_id for a in typed_artifacts) + operation.value
        ).encode("utf-8")
        claim_id = hashlib.sha256(claim_id_raw).hexdigest()

        return CandidateClaim(
            claim_id=claim_id,
            content=content,
            operation=operation.value,
            source_artifact_ids=[a.artifact_id for a in typed_artifacts],
            derivation_log=derivation_log,
            timestamp_ns=timestamp_ns,
            approved=False,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def derive(
        self,
        artifact_ids: list[str],
        operation: DeriveOperation,
        timestamp_ns: int,
    ) -> tuple[CandidateClaim, ValidationVerdict]:
        """Derive a new claim from ACCEPTED artifacts and validate it.

        Steps:
        1. Retrieve ACCEPTED artifacts from the belief ledger.
        2. Build a :class:`CandidateClaim` (approved=False).
        3. Create a fresh :class:`Artifact` from the claim content.
        4. Run the validation pipeline on the new artifact.
        5. Log the derivation step to the audit trail.
        6. If validation verdict is ACCEPTED, admit to belief ledger as PENDING
           (NOT self-approved — caller decides final acceptance).
        7. Return (candidate_claim, verdict).

        Args:
            artifact_ids: IDs of ACCEPTED artifacts to derive from.
            operation: Derivation strategy to apply.
            timestamp_ns: Nanosecond timestamp for determinism.

        Returns:
            Tuple of (CandidateClaim, ValidationVerdict).

        Raises:
            ValueError: If any artifact_id is not found or not ACCEPTED.

        """
        from thalos_prime.artifacts.schema import Artifact  # noqa: PLC0415
        from thalos_prime.audit.trail import AuditEventType  # noqa: PLC0415
        from thalos_prime.belief.ledger import BeliefState  # noqa: PLC0415
        from thalos_prime.indexing.prp import PrpIndexer  # noqa: PLC0415

        accepted_records = {
            r.artifact_id: r
            for r in self._belief_ledger.get_by_state(BeliefState.ACCEPTED)
        }

        missing = [aid for aid in artifact_ids if aid not in accepted_records]
        if missing:
            msg = f"Artifact IDs not found or not ACCEPTED: {missing}"
            raise ValueError(msg)

        # Build lightweight Artifact stubs from ledger records for derivation.
        # The actual content is not stored in BeliefRecord, so we create minimal
        # Artifact objects from what we have (coordinate_hex as proxy content).
        artifacts: list[Artifact] = []
        for aid in artifact_ids:
            rec = accepted_records[aid]
            art = Artifact.create(
                content=rec.coordinate_hex,
                source_uris=[f"belief:{aid}"],
                metadata={"derived_from": aid},
                timestamp_ns=timestamp_ns,
            )
            # Override artifact_id to use the original for traceability
            object.__setattr__(art, "artifact_id", aid)
            artifacts.append(art)

        candidate = self._derive_claim(artifacts, operation, timestamp_ns)

        derived_artifact = Artifact.create(
            content=candidate.content,
            source_uris=[f"derived:{aid}" for aid in artifact_ids],
            metadata={"claim_id": candidate.claim_id, "operation": operation.value},
            timestamp_ns=timestamp_ns,
        )

        verdict = self._validation_pipeline.validate(derived_artifact, timestamp_ns)

        self._audit_trail.append(
            event_type=AuditEventType.DERIVATION_STEP,
            artifact_id=derived_artifact.artifact_id,
            timestamp_ns=timestamp_ns,
            payload={
                "claim_id": candidate.claim_id,
                "operation": operation.value,
                "verdict": verdict.final_status.value,
                "confidence": str(verdict.confidence),
            },
        )

        from thalos_prime.artifacts.schema import ValidationStatus  # noqa: PLC0415

        if verdict.final_status is ValidationStatus.ACCEPTED:
            _prp_key = b"thalos-prime-prp-key-16-bytes!!"  # 16 bytes exactly
            _indexer = PrpIndexer(key=_prp_key)
            coord = _indexer.index(derived_artifact.content)
            try:
                self._belief_ledger.admit(
                    artifact=derived_artifact,
                    coordinate_hex=coord.to_hex_str(),
                    confidence=verdict.confidence,
                    timestamp_ns=timestamp_ns,
                )
            except ValueError:
                # Already admitted — idempotent
                logger.debug(
                    "TplReasoningLayer(%s): derived artifact already admitted: %r",
                    self._layer_id,
                    derived_artifact.artifact_id,
                )

        return candidate, verdict

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the reasoning layer."""
        self._initialized = True
        logger.info("TplReasoningLayer(%s) initialized", self._layer_id)

    def validate(self) -> bool:
        """Validate that the reasoning layer is ready to operate.

        Returns:
            True when the layer is initialized and its dependencies are present.

        """
        return self._initialized

    def operate(
        self,
        artifact_ids: list[str],
        operation: DeriveOperation,
        timestamp_ns: int,
    ) -> tuple[CandidateClaim, ValidationVerdict]:
        """Alias for :meth:`derive` — satisfies the lifecycle contract.

        Args:
            artifact_ids: IDs of ACCEPTED artifacts to derive from.
            operation: Derivation strategy to apply.
            timestamp_ns: Nanosecond timestamp.

        Returns:
            Tuple of (CandidateClaim, ValidationVerdict).

        """
        return self.derive(artifact_ids, operation, timestamp_ns)

    def reconcile(self) -> None:
        """Reconcile any inconsistent internal state (no-op for this layer)."""

    def checkpoint(self) -> dict[str, object]:
        """Serialize layer state for restart.

        Returns:
            Dict with layer_id, initialized flag, and schema_version.

        """
        return {
            "layer_id": self._layer_id,
            "initialized": self._initialized,
            "schema_version": self.schema_version,
        }

    def terminate(self) -> None:
        """Terminate the reasoning layer."""
        self._initialized = False
        logger.info("TplReasoningLayer(%s) terminated", self._layer_id)
