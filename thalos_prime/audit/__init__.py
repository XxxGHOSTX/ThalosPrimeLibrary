"""Thalos Prime - Tamper-evident Audit Trail subsystem.

Provides an append-only, SHA-256-chained structured event log for
state transitions, derivation steps, and lifecycle milestones.
Tampering at any position is detectable via chain verification.
"""

from thalos_prime.audit.trail import (
    AuditEvent,
    AuditEventType,
    AuditTrail,
)

__all__ = [
    "AuditEvent",
    "AuditEventType",
    "AuditTrail",
]
