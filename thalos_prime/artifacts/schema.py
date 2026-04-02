"""Canonical Artifact Schema for ThalosPrime Library.

Control Plane module: defines the canonical data structures for artifacts,
provenance, derivation, FACS bundles, and Genesis Lock signing.

All structures are serializable (Pydantic BaseModel), versioned, and
deterministic. Every field is explicitly typed.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from enum import StrEnum
from typing import ClassVar

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import hmac as crypto_hmac
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Pre-compiled pattern for whitespace normalisation: one-or-more whitespace → single space
_WHITESPACE_RE = re.compile(r"\s+")


class ValidationStatus(StrEnum):
    """Validation status values for an Artifact.

    Members:
        PENDING: Initial state; not yet reviewed.
        ACCEPTED: Artifact has been validated and accepted.
        DISPUTED: Artifact content is under dispute.
        REJECTED: Artifact has been formally rejected.

    """

    PENDING = "pending"
    ACCEPTED = "accepted"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class DerivationStep(BaseModel):
    """A single step in a derivation chain.

    Attributes:
        step_id: Deterministic hash of the step inputs.
        operation: Name of the operation performed.
        input_ids: Ordered list of artifact IDs consumed by this step.
        output_id: Artifact ID produced by this step.
        timestamp_ns: Nanosecond-precision creation timestamp.
        config_hash: SHA-256 hex digest of the configuration used.

    """

    step_id: str
    operation: str
    input_ids: list[str]
    output_id: str
    timestamp_ns: int
    config_hash: str


class ProvenanceNode(BaseModel):
    """A node in the artifact provenance graph.

    Each node records which artifacts it derives from, the derivation steps
    applied, an optional source URI, and version metadata.

    Attributes:
        node_id: Unique identifier for this provenance node.
        artifact_id: ID of the artifact this node describes.
        parent_ids: IDs of parent provenance nodes.
        derivation_steps: Ordered sequence of derivation steps.
        source_uri: Optional URI of the original data source.
        created_at_ns: Nanosecond-precision creation timestamp.
        version: Monotonically increasing revision counter.

    """

    node_id: str
    artifact_id: str
    parent_ids: list[str]
    derivation_steps: list[DerivationStep]
    source_uri: str | None = None
    created_at_ns: int
    version: int


class FacsBundle(BaseModel):
    """Flags, Annotations, Contradiction maps, and Suspension logs.

    Bundles epistemic metadata that travels with an artifact through
    validation workflows.

    Attributes:
        flags: Named boolean flags, e.g. ``{"disputed": True}``.
        annotations: Free-form key/value string annotations.
        contradiction_map: Maps an artifact_id to a list of conflicting IDs.
        suspension_log: Ordered list of suspension event records.
        schema_version: Bundle schema version for forward-compatibility.

    """

    flags: dict[str, bool] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    contradiction_map: dict[str, list[str]] = Field(default_factory=dict)
    suspension_log: list[dict[str, str]] = Field(default_factory=list)
    schema_version: int = 1


class Artifact(BaseModel):
    """The canonical artifact — the core unit of the ThalosPrime knowledge store.

    All IDs are deterministic SHA-256 digests derived from content. The
    canonical form is the content after lowercasing, stripping, and whitespace
    normalisation.

    Attributes:
        artifact_id: SHA-256 hex digest of ``canonical_form``.
        content: Raw input content.
        content_hash: SHA-256 hex digest of ``content``.
        canonical_form: Lowercased, stripped, whitespace-normalised content.
        metadata: Free-form string key/value metadata.
        validation_status: Current validation state.
        confidence: Confidence score in ``[0.0, 1.0]``.
        source_uris: List of source reference URIs.
        provenance: Optional provenance graph node.
        facs: Optional FACS bundle.
        signature: Optional Genesis Lock HMAC-SHA256 hex signature.
        timestamp_ns: Nanosecond-precision creation timestamp.
        temporal_scope: Optional ``(start_ns, end_ns)`` validity window.
        version: Artifact revision counter.
        schema_version: Schema format version for forward-compatibility.

    """

    artifact_id: str
    content: str
    content_hash: str
    canonical_form: str
    metadata: dict[str, str] = Field(default_factory=dict)
    validation_status: ValidationStatus = ValidationStatus.PENDING
    confidence: float = 0.0
    source_uris: list[str] = Field(default_factory=list)
    provenance: ProvenanceNode | None = None
    facs: FacsBundle | None = None
    signature: str | None = None
    timestamp_ns: int
    temporal_scope: tuple[int, int] | None = None
    version: int = 1
    schema_version: int = 1

    @classmethod
    def create(
        cls,
        content: str,
        source_uris: list[str],
        metadata: dict[str, str] | None = None,
        timestamp_ns: int | None = None,
    ) -> Artifact:
        """Create an Artifact with deterministic IDs derived from content.

        The ``content_hash`` is the SHA-256 digest of the raw content bytes.
        The ``canonical_form`` is the content lowercased, stripped, and
        whitespace-normalised. The ``artifact_id`` is the SHA-256 digest of
        ``canonical_form``.

        Args:
            content: Raw content string for the artifact.
            source_uris: List of source reference URIs.
            metadata: Optional free-form string key/value metadata.
            timestamp_ns: Optional nanosecond timestamp; defaults to
                ``time.time_ns()`` when not provided.

        Returns:
            A fully populated :class:`Artifact` instance.

        """
        ts = timestamp_ns if timestamp_ns is not None else time.time_ns()
        canonical = _WHITESPACE_RE.sub(" ", content.lower().strip())
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        artifact_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return cls(
            artifact_id=artifact_id,
            content=content,
            content_hash=content_hash,
            canonical_form=canonical,
            metadata=metadata or {},
            source_uris=source_uris,
            timestamp_ns=ts,
        )


class GenesisLock:
    """HMAC-SHA256 signing utility for artifact integrity verification.

    Signs and verifies artifacts using a canonical string representation
    derived from their immutable identity fields.
    """

    #: The canonical template used for signing: ``artifact_id:content_hash:status:version``
    _CANONICAL_TEMPLATE: ClassVar[str] = "{artifact_id}:{content_hash}:{status}:{version}"

    def __init__(self, key: bytes) -> None:
        """Initialise Genesis Lock with an HMAC signing key.

        Args:
            key: Raw bytes to use as the HMAC-SHA256 signing key.

        """
        self._key = key

    def sign(self, artifact: Artifact) -> str:
        """Produce an HMAC-SHA256 hex signature for *artifact*.

        The canonical representation signed is:
        ``{artifact_id}:{content_hash}:{validation_status}:{version}``
        encoded as UTF-8.

        Args:
            artifact: The artifact to sign.

        Returns:
            Lowercase hex-encoded HMAC-SHA256 digest.

        """
        canonical = self._CANONICAL_TEMPLATE.format(
            artifact_id=artifact.artifact_id,
            content_hash=artifact.content_hash,
            status=artifact.validation_status.value,
            version=artifact.version,
        ).encode("utf-8")
        h = crypto_hmac.HMAC(self._key, hashes.SHA256())
        h.update(canonical)
        digest: bytes = h.finalize()
        return digest.hex()

    def verify(self, artifact: Artifact, signature: str) -> bool:
        """Verify that *signature* matches the expected HMAC for *artifact*.

        Args:
            artifact: The artifact whose signature is being verified.
            signature: Lowercase hex-encoded HMAC-SHA256 digest to verify.

        Returns:
            ``True`` if the signature matches, ``False`` otherwise.

        """
        expected = self.sign(artifact)
        return expected == signature


__all__ = [
    "Artifact",
    "DerivationStep",
    "FacsBundle",
    "GenesisLock",
    "ProvenanceNode",
    "ValidationStatus",
]
