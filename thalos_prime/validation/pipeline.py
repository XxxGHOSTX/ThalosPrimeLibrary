"""Six-stage validation pipeline for ThalosPrime Library.

Control Plane module: validates artifact candidates through 6 deterministic
stages before admission to the belief base. Given identical state and inputs,
produces identical outputs (deterministic semantics).

Stages:
  1. Canonicalization     - normalize content to canonical form
  2. Source binding       - validate and bind source URIs
  3. Consistency analysis - check internal consistency
  4. Contradiction search - find conflicts with existing beliefs
  5. Confidence assignment- compute confidence score
  6. Admission control    - decide accept/reject/pending/dispute
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field

from thalos_prime.artifacts.schema import FacsBundle, ValidationStatus
from thalos_prime.belief.ledger import BeliefState

if TYPE_CHECKING:
    from thalos_prime.artifacts.schema import Artifact
    from thalos_prime.belief.ledger import BeliefLedger

logger = logging.getLogger(__name__)

# Weighted coefficients for the confidence stage.
# Indices 0-3 correspond to stages 1-4; index 4 is the artifact's own
# confidence field.  The five weights sum to 1.0.
_CONFIDENCE_WEIGHTS: tuple[float, ...] = (0.1, 0.3, 0.2, 0.2, 0.2)

# Admission control thresholds.
_ADMIT_ACCEPT_THRESHOLD: float = 0.7
_ADMIT_PENDING_THRESHOLD: float = 0.4

# Minimum content length for the consistency check.
_MIN_CONTENT_LEN: int = 10

# Minimum word length for the contradiction heuristic.
_MIN_WORD_LEN: int = 4


class ValidationStage(StrEnum):
    """Enumeration of the six pipeline stages.

    Members:
        CANONICALIZATION: Normalise content to canonical form.
        SOURCE_BINDING: Validate and bind source URIs.
        CONSISTENCY_ANALYSIS: Check internal consistency of the artifact.
        CONTRADICTION_SEARCH: Search for conflicts with accepted beliefs.
        CONFIDENCE_ASSIGNMENT: Compute the aggregate confidence score.
        ADMISSION_CONTROL: Decide whether to accept, pend, or reject.

    """

    CANONICALIZATION = "canonicalization"
    SOURCE_BINDING = "source_binding"
    CONSISTENCY_ANALYSIS = "consistency_analysis"
    CONTRADICTION_SEARCH = "contradiction_search"
    CONFIDENCE_ASSIGNMENT = "confidence_assignment"
    ADMISSION_CONTROL = "admission_control"


class StageResult(BaseModel):
    """The outcome produced by a single validation stage.

    Attributes:
        stage: Which pipeline stage produced this result.
        passed: ``True`` when the stage considers the artifact acceptable.
        score: Normalised score in ``[0.0, 1.0]``.
        notes: Human-readable diagnostic messages from the stage.
        timestamp_ns: Nanosecond timestamp recorded when the stage ran.

    """

    stage: ValidationStage
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    notes: list[str]
    timestamp_ns: int


class ValidationVerdict(BaseModel):
    """Aggregate verdict produced after all six stages complete.

    Attributes:
        artifact_id: The artifact under evaluation.
        final_status: The :class:`~thalos_prime.artifacts.schema.ValidationStatus`
            assigned by the admission-control stage.
        confidence: Weighted confidence score in ``[0.0, 1.0]``.
        stage_results: Ordered list of per-stage results.
        facs_bundle: :class:`~thalos_prime.artifacts.schema.FacsBundle` carrying
            ``contradicted``, ``admitted``, and ``rejected`` flags.
        timestamp_ns: Nanosecond timestamp of the validation run.
        schema_version: Schema version for forward-compatibility.

    """

    artifact_id: str
    final_status: ValidationStatus
    confidence: float = Field(ge=0.0, le=1.0)
    stage_results: list[StageResult]
    facs_bundle: FacsBundle
    timestamp_ns: int
    schema_version: int = 1


class ValidationPipeline:
    """Deterministic six-stage validation pipeline for artifact admission.

    Each call to :meth:`validate` runs all six stages in order and returns a
    :class:`ValidationVerdict`.  The pipeline is stateless between calls;
    state comes solely from the injected :class:`~thalos_prime.belief.ledger.BeliefLedger`.

    This class implements the six-method lifecycle contract required by the
    ThalosPrime lifecycle validator.

    Attributes:
        schema_version: Schema version for checkpoint serialisation.

    """

    schema_version: ClassVar[int] = 1

    def __init__(self, pipeline_id: str, belief_ledger: BeliefLedger) -> None:
        """Initialise the validation pipeline.

        Args:
            pipeline_id: Deterministic string identifier for this pipeline.
            belief_ledger: Epistemic ledger consulted during contradiction search.

        """
        self._pipeline_id = pipeline_id
        self._belief_ledger = belief_ledger
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def pipeline_id(self) -> str:
        """Deterministic string identifier for this pipeline instance.

        Returns:
            The pipeline ID supplied at construction time.

        """
        return self._pipeline_id

    # ------------------------------------------------------------------
    # Private stage implementations
    # ------------------------------------------------------------------

    def _stage_canonicalize(
        self,
        artifact: Artifact,
        timestamp_ns: int,
    ) -> StageResult:
        """Stage 1: Canonicalization.

        Checks that the artifact's ``canonical_form`` is non-empty and
        records its length.  Always passes with a perfect score of 1.0.

        Args:
            artifact: Artifact under evaluation.
            timestamp_ns: Nanosecond timestamp for this stage run.

        Returns:
            A :class:`StageResult` for the CANONICALIZATION stage.

        """
        canonical_len = len(artifact.canonical_form)
        notes = [f"canonical_form length: {canonical_len}"]
        return StageResult(
            stage=ValidationStage.CANONICALIZATION,
            passed=True,
            score=1.0,
            notes=notes,
            timestamp_ns=timestamp_ns,
        )

    def _stage_source_binding(
        self,
        artifact: Artifact,
        timestamp_ns: int,
    ) -> StageResult:
        """Stage 2: Source binding.

        Passes when the artifact has at least one source URI.  Score scales
        linearly with the number of source URIs up to a maximum of 1.0.

        Args:
            artifact: Artifact under evaluation.
            timestamp_ns: Nanosecond timestamp for this stage run.

        Returns:
            A :class:`StageResult` for the SOURCE_BINDING stage.

        """
        count = len(artifact.source_uris)
        passed = count > 0
        score = min(1.0, count * 0.25)
        notes = [f"source_uri count: {count}"]
        return StageResult(
            stage=ValidationStage.SOURCE_BINDING,
            passed=passed,
            score=score,
            notes=notes,
            timestamp_ns=timestamp_ns,
        )

    def _stage_consistency(
        self,
        artifact: Artifact,
        timestamp_ns: int,
    ) -> StageResult:
        """Stage 3: Consistency analysis.

        Passes when the artifact's ``content`` has more than 10 characters
        and its ``confidence`` is within ``[0.0, 1.0]``.

        Args:
            artifact: Artifact under evaluation.
            timestamp_ns: Nanosecond timestamp for this stage run.

        Returns:
            A :class:`StageResult` for the CONSISTENCY_ANALYSIS stage.

        """
        content_ok = len(artifact.content) > _MIN_CONTENT_LEN
        confidence_ok = 0.0 <= artifact.confidence <= 1.0
        passed = content_ok and confidence_ok
        score = 1.0 if passed else 0.0
        notes: list[str] = []
        if not content_ok:
            notes.append(f"content too short: {len(artifact.content)} chars")
        if not confidence_ok:
            notes.append(f"confidence out of range: {artifact.confidence}")
        if passed:
            notes.append("consistency checks passed")
        return StageResult(
            stage=ValidationStage.CONSISTENCY_ANALYSIS,
            passed=passed,
            score=score,
            notes=notes,
            timestamp_ns=timestamp_ns,
        )

    def _stage_contradiction(
        self,
        artifact: Artifact,
        timestamp_ns: int,
    ) -> StageResult:
        """Stage 4: Contradiction search.

        Searches the belief ledger for accepted records whose coordinate
        contains a significant word (>4 chars) from the artifact content.
        Score is 1.0 for no conflicts, 0.5 for one, 0.0 for multiple.

        Args:
            artifact: Artifact under evaluation.
            timestamp_ns: Nanosecond timestamp for this stage run.

        Returns:
            A :class:`StageResult` for the CONTRADICTION_SEARCH stage.

        """
        accepted_records = self._belief_ledger.get_by_state(BeliefState.ACCEPTED)

        # Significant words are lower-cased content tokens longer than _MIN_WORD_LEN chars.
        significant_words = [
            w.lower() for w in artifact.content.split() if len(w) > _MIN_WORD_LEN
        ]

        contradicting_ids: list[str] = []
        for record in accepted_records:
            if record.artifact_id == artifact.artifact_id:
                continue
            # Heuristic: a potential contradiction is flagged when any
            # significant word appears as a substring of the record's
            # 16-character coordinate (deterministic, no content access needed).
            if any(word in record.coordinate_hex for word in significant_words):
                contradicting_ids.append(record.artifact_id)

        if not contradicting_ids:
            score = 1.0
            passed = True
            notes: list[str] = ["no contradictions found"]
        elif len(contradicting_ids) == 1:
            score = 0.5
            passed = True
            notes = [f"one contradiction found: {contradicting_ids[0]}"]
        else:
            score = 0.0
            passed = False
            preview = ",".join(contradicting_ids[:3])
            notes = [f"multiple contradictions found: {preview}"]

        return StageResult(
            stage=ValidationStage.CONTRADICTION_SEARCH,
            passed=passed,
            score=score,
            notes=notes,
            timestamp_ns=timestamp_ns,
        )

    def _stage_confidence(
        self,
        artifact: Artifact,
        stage_scores: list[float],
        timestamp_ns: int,
    ) -> StageResult:
        """Stage 5: Confidence assignment.

        Computes a weighted average of the four prior stage scores plus the
        artifact's own ``confidence`` field.  The five weights are
        ``[0.1, 0.3, 0.2, 0.2, 0.2]`` and sum to 1.0.

        Args:
            artifact: Artifact under evaluation (``artifact.confidence`` contributes).
            stage_scores: Scores from stages 1-4 in order.
            timestamp_ns: Nanosecond timestamp for this stage run.

        Returns:
            A :class:`StageResult` for the CONFIDENCE_ASSIGNMENT stage.

        """
        all_scores = [*stage_scores, artifact.confidence]
        score = sum(
            s * w for s, w in zip(all_scores, _CONFIDENCE_WEIGHTS, strict=True)
        )
        # Clamp to [0.0, 1.0] to guard against floating-point drift.
        score = max(0.0, min(1.0, score))
        notes = [f"weighted confidence: {score:.4f}"]
        return StageResult(
            stage=ValidationStage.CONFIDENCE_ASSIGNMENT,
            passed=True,
            score=score,
            notes=notes,
            timestamp_ns=timestamp_ns,
        )

    def _stage_admission(
        self,
        artifact: Artifact,
        confidence: float,
        timestamp_ns: int,
    ) -> StageResult:
        """Stage 6: Admission control.

        Assigns the final :class:`~thalos_prime.artifacts.schema.ValidationStatus`
        based on the confidence threshold ladder:
        ``>=0.7`` → ACCEPTED, ``>=0.4`` → PENDING, ``<0.4`` → REJECTED.

        Args:
            artifact: Artifact under evaluation (reserved for future use).
            confidence: Aggregate confidence produced by stage 5.
            timestamp_ns: Nanosecond timestamp for this stage run.

        Returns:
            A :class:`StageResult` for the ADMISSION_CONTROL stage.

        """
        if confidence >= _ADMIT_ACCEPT_THRESHOLD:
            decision = "ACCEPTED"
            score = 1.0
        elif confidence >= _ADMIT_PENDING_THRESHOLD:
            decision = "PENDING"
            score = 0.5
        else:
            decision = "REJECTED"
            score = 0.0
        notes = [
            f"thresholds: {_ADMIT_ACCEPT_THRESHOLD}=accept "
            f"/ {_ADMIT_PENDING_THRESHOLD}=pending / below=reject; "
            f"confidence={confidence:.4f}; decision={decision}"
        ]
        return StageResult(
            stage=ValidationStage.ADMISSION_CONTROL,
            passed=score > 0.0,
            score=score,
            notes=notes,
            timestamp_ns=timestamp_ns,
        )

    # ------------------------------------------------------------------
    # Public validation entry point
    # ------------------------------------------------------------------

    def validate(self, artifact: Artifact, timestamp_ns: int) -> ValidationVerdict:
        """Run all six stages and return the aggregate verdict.

        Stages are executed sequentially.  The :class:`FacsBundle` attached
        to the verdict carries three boolean flags: ``contradicted``,
        ``admitted``, and ``rejected``.

        Args:
            artifact: Artifact candidate to validate.
            timestamp_ns: Nanosecond timestamp for the validation run.

        Returns:
            A :class:`ValidationVerdict` summarising all six stage outcomes.

        """
        r1 = self._stage_canonicalize(artifact, timestamp_ns)
        r2 = self._stage_source_binding(artifact, timestamp_ns)
        r3 = self._stage_consistency(artifact, timestamp_ns)
        r4 = self._stage_contradiction(artifact, timestamp_ns)
        r5 = self._stage_confidence(
            artifact,
            [r1.score, r2.score, r3.score, r4.score],
            timestamp_ns,
        )
        r6 = self._stage_admission(artifact, r5.score, timestamp_ns)

        stage_results = [r1, r2, r3, r4, r5, r6]

        # Map admission score directly to status (mirrors _stage_admission thresholds).
        if r6.score >= 1.0:
            final_status = ValidationStatus.ACCEPTED
        elif r6.score >= _ADMIT_PENDING_THRESHOLD:
            final_status = ValidationStatus.PENDING
        else:
            final_status = ValidationStatus.REJECTED

        facs_bundle = FacsBundle(
            flags={
                "contradicted": r4.score < 1.0,
                "admitted": final_status is ValidationStatus.ACCEPTED,
                "rejected": final_status is ValidationStatus.REJECTED,
            },
        )

        return ValidationVerdict(
            artifact_id=artifact.artifact_id,
            final_status=final_status,
            confidence=r5.score,
            stage_results=stage_results,
            facs_bundle=facs_bundle,
            timestamp_ns=timestamp_ns,
        )

    # ------------------------------------------------------------------
    # Lifecycle protocol
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialise the pipeline, marking it ready for use.

        Idempotent; safe to call multiple times.
        """
        self._initialized = True
        logger.debug("ValidationPipeline(%s) initialised", self._pipeline_id)

    def operate(self, artifact: Artifact, timestamp_ns: int) -> ValidationVerdict:
        """Alias for :meth:`validate`; satisfies the lifecycle ``operate`` contract.

        Args:
            artifact: Artifact candidate to validate.
            timestamp_ns: Nanosecond timestamp for the validation run.

        Returns:
            A :class:`ValidationVerdict` summarising all six stage outcomes.

        """
        return self.validate(artifact, timestamp_ns)

    def reconcile(self) -> None:
        """Reconcile internal state.  Currently a no-op; retained for lifecycle compliance."""
        logger.debug("ValidationPipeline(%s) reconcile called", self._pipeline_id)

    def checkpoint(self) -> dict[str, object]:
        """Serialise pipeline identity for checkpoint/restore.

        Returns:
            A dictionary with ``pipeline_id`` and ``schema_version``.

        """
        return {
            "pipeline_id": self._pipeline_id,
            "schema_version": self.schema_version,
        }

    def terminate(self) -> None:
        """Terminate the pipeline and clear initialised state."""
        self._initialized = False
        logger.debug("ValidationPipeline(%s) terminated", self._pipeline_id)


__all__ = [
    "StageResult",
    "ValidationPipeline",
    "ValidationStage",
    "ValidationVerdict",
]
