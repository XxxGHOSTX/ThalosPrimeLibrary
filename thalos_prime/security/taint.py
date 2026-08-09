"""Untrusted-content and capability enforcement for Thalos Prime.

Retrieved documents are evidence candidates, never executable instructions.
This module provides explicit taint labels, capability checks, and approval
receipts for state-changing operations.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from thalos_prime.epistemic_core import content_id


class TaintLabel(StrEnum):
    EXTERNAL_CONTENT = "external_content"
    USER_ASSERTION = "user_assertion"
    MODEL_GENERATED = "model_generated"
    SYNTHETIC = "synthetic"
    VERIFIED_SOURCE = "verified_source"


class Capability(StrEnum):
    READ_ARTIFACT = "read:artifact"
    READ_BELIEF = "read:belief"
    READ_AUDIT = "read:audit"
    WRITE_ARTIFACT = "write:artifact"
    WRITE_SNAPSHOT = "write:snapshot"
    WRITE_CLAIM = "write:claim"
    WRITE_EVIDENCE = "write:evidence"
    WRITE_EVALUATION = "write:evaluation"
    COMMIT_BELIEF = "commit:belief"
    RETRACT_BELIEF = "retract:belief"
    EXPORT_PROOF = "export:proof"


class Principal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    principal_id: str
    capabilities: frozenset[Capability]

    @classmethod
    def create(cls, principal_id: str, capabilities: Iterable[Capability]) -> "Principal":
        return cls(principal_id=principal_id, capabilities=frozenset(capabilities))

    def require(self, capability: Capability) -> None:
        if capability not in self.capabilities:
            raise PermissionError(
                f"principal {self.principal_id!r} lacks capability {capability.value!r}"
            )


class TaintedValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: str
    labels: frozenset[TaintLabel]
    origin_id: str | None = None

    @property
    def executable(self) -> bool:
        return False

    def add(self, *labels: TaintLabel) -> "TaintedValue":
        return self.model_copy(update={"labels": frozenset(set(self.labels) | set(labels))})


class ApprovalReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    principal_id: str
    action: Capability
    target_id: str
    request_hash: str
    nonce: str = Field(min_length=8)

    @classmethod
    def create(
        cls,
        *,
        principal_id: str,
        action: Capability,
        target_id: str,
        request_hash: str,
        nonce: str,
    ) -> "ApprovalReceipt":
        payload = {
            "principal_id": principal_id,
            "action": action.value,
            "target_id": target_id,
            "request_hash": request_hash,
            "nonce": nonce,
        }
        return cls(
            receipt_id=content_id("approval", payload),
            principal_id=principal_id,
            action=action,
            target_id=target_id,
            request_hash=request_hash,
            nonce=nonce,
        )

    def validate_for(
        self,
        *,
        principal: Principal,
        action: Capability,
        target_id: str,
        request_hash: str,
    ) -> None:
        principal.require(action)
        if self.principal_id != principal.principal_id:
            raise PermissionError("approval principal mismatch")
        if self.action is not action:
            raise PermissionError("approval action mismatch")
        if self.target_id != target_id:
            raise PermissionError("approval target mismatch")
        if self.request_hash != request_hash:
            raise PermissionError("approval request hash mismatch")


READ_ONLY_PRINCIPAL = Principal.create(
    "anonymous-read",
    [Capability.READ_ARTIFACT, Capability.READ_BELIEF, Capability.READ_AUDIT],
)


__all__ = [
    "ApprovalReceipt",
    "Capability",
    "Principal",
    "READ_ONLY_PRINCIPAL",
    "TaintLabel",
    "TaintedValue",
]
