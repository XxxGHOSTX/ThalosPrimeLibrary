"""Signed human directives and operation allowlists for ThalosPrime experiments.

This module adapts the Human Directive Record concept from ThalosPrimeConcept.
It records the human-defined objective and limits, supports RSA-PSS signatures,
and exposes an explicit authorization check. It does not execute operations.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import BaseModel, ConfigDict, Field, field_validator

from thalos_prime.experiments.contracts import ExperimentSpec

_MAX_DIRECTIVE_PAYLOAD_BYTES = 64 * 1_024
_MAX_DIRECTIVE_LIST_ITEMS = 100
_MAX_DIRECTIVE_TEXT_LENGTH = 2_000


class HumanDirectiveRecord(BaseModel):
    """Human-defined task, constraints, acceptance criteria, and permissions.

    The signature covers the canonical payload including the signer identity.
    Any change to signed task fields invalidates the signature. The operation
    allowlist is exact-match and deny-by-default: an unsigned directive or an
    operation not explicitly permitted cannot authorize execution.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    directive_id: str = Field(min_length=1, max_length=200)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    objectives: list[str] = Field(min_length=1, max_length=_MAX_DIRECTIVE_LIST_ITEMS)
    constraints: list[str] = Field(default_factory=list, max_length=_MAX_DIRECTIVE_LIST_ITEMS)
    parameters: dict[str, object] = Field(default_factory=dict, max_length=100)
    success_criteria: list[str] = Field(min_length=1, max_length=_MAX_DIRECTIVE_LIST_ITEMS)
    prohibited_actions: list[str] = Field(default_factory=list, max_length=_MAX_DIRECTIVE_LIST_ITEMS)
    prohibited_operations: list[str] = Field(default_factory=list, max_length=_MAX_DIRECTIVE_LIST_ITEMS)
    permitted_operations: list[str] = Field(default_factory=list, max_length=_MAX_DIRECTIVE_LIST_ITEMS)
    signer: str | None = Field(default=None, max_length=200)
    signature: str | None = Field(default=None, max_length=2_000)
    schema_version: int = Field(default=1, ge=1)

    @field_validator("directive_id", "signer")
    @classmethod
    def validate_identity_text(cls, value: str | None) -> str | None:
        """Normalize optional signer and required directive identifiers."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("directive ID or signer must not be blank")
        return normalized

    @field_validator("timestamp")
    @classmethod
    def require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        """Normalize timestamps to UTC to make the signing payload unambiguous."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("directive timestamp must include a timezone")
        return value.astimezone(timezone.utc)

    @field_validator(
        "objectives",
        "constraints",
        "success_criteria",
        "prohibited_actions",
        "prohibited_operations",
        "permitted_operations",
    )
    @classmethod
    def normalize_string_lists(cls, values: list[str]) -> list[str]:
        """Reject blank items and normalize harmless surrounding whitespace."""
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("directive list items must not be blank")
        if any(len(value) > _MAX_DIRECTIVE_TEXT_LENGTH for value in normalized):
            raise ValueError(
                f"directive list items must be at most {_MAX_DIRECTIVE_TEXT_LENGTH} characters"
            )
        if len(normalized) != len(set(normalized)):
            raise ValueError("directive list items must be unique")
        return normalized

    def to_signing_payload(self) -> bytes:
        """Return canonical JSON bytes for all fields except the signature."""
        payload = self.model_dump(mode="json", exclude={"signature"})
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        if len(encoded) > _MAX_DIRECTIVE_PAYLOAD_BYTES:
            raise ValueError(
                f"directive signing payload exceeds {_MAX_DIRECTIVE_PAYLOAD_BYTES} bytes"
            )
        return encoded

    @property
    def directive_digest(self) -> str:
        """Return the SHA-256 digest of the canonical signed payload."""
        return hashlib.sha256(self.to_signing_payload()).hexdigest()

    def sign(self, private_key: rsa.RSAPrivateKey, signer_id: str) -> None:
        """Sign this directive using RSA-PSS with SHA-256."""
        normalized_signer = signer_id.strip()
        if not normalized_signer:
            raise ValueError("signer_id must not be blank")
        self.signer = normalized_signer
        signature = private_key.sign(
            self.to_signing_payload(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        self.signature = base64.b64encode(signature).decode("ascii")

    def verify(self, public_key: rsa.RSAPublicKey) -> bool:
        """Verify the signature against this exact directive state."""
        if not self.signature or not self.signer:
            return False
        try:
            signature = base64.b64decode(self.signature, validate=True)
            public_key.verify(
                signature,
                self.to_signing_payload(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
        except (InvalidSignature, ValueError, TypeError, RecursionError, binascii.Error):
            return False
        return True

    def authorize_operation(
        self,
        operation_name: str,
        public_key: rsa.RSAPublicKey,
    ) -> None:
        """Raise PermissionError unless the signed directive permits the operation."""
        normalized_operation = operation_name.strip()
        if not normalized_operation:
            raise PermissionError("operation name must not be blank")
        if not self.verify(public_key):
            raise PermissionError("directive signature is missing or invalid")
        if normalized_operation in self.prohibited_operations:
            raise PermissionError(f"operation {normalized_operation!r} is prohibited")
        if normalized_operation not in self.permitted_operations:
            raise PermissionError(f"operation {normalized_operation!r} is not explicitly permitted")


def authorize_experiment_operation(
    spec: ExperimentSpec,
    directive: HumanDirectiveRecord,
    operation_name: str,
    public_key: rsa.RSAPublicKey,
) -> None:
    """Authorize an operation only when the spec binds to this signed directive.

    This validates the human task contract and its exact digest before
    checking the operation allowlist. It does not execute the operation.
    """
    if spec.directive_id is None or spec.directive_digest is None:
        raise PermissionError("experiment spec is not bound to a human directive")
    if spec.directive_id != directive.directive_id:
        raise PermissionError("experiment directive ID does not match the signed directive")
    if spec.directive_digest != directive.directive_digest:
        raise PermissionError("experiment directive digest does not match the signed directive")
    directive.authorize_operation(operation_name, public_key)


__all__ = ["HumanDirectiveRecord", "authorize_experiment_operation"]
