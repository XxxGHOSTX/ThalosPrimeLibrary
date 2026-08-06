"""Security primitives for Thalos Prime."""

from thalos_prime.security.taint import (
    ApprovalReceipt,
    Capability,
    Principal,
    READ_ONLY_PRINCIPAL,
    TaintLabel,
    TaintedValue,
)

__all__ = [
    "ApprovalReceipt",
    "Capability",
    "Principal",
    "READ_ONLY_PRINCIPAL",
    "TaintLabel",
    "TaintedValue",
]
