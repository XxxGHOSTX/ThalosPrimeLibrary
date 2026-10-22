"""Tests for signed directives and explicit operation authorization."""

from __future__ import annotations

from datetime import datetime

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError

from thalos_prime.experiments.directive import HumanDirectiveRecord


def make_directive() -> HumanDirectiveRecord:
    """Build a stable directive whose permitted operation is explicit."""
    return HumanDirectiveRecord(
        directive_id="hdr-representation-test",
        timestamp=datetime.fromisoformat("2026-10-22T12:00:00+00:00"),
        objectives=["Compare graph and constraint representations"],
        constraints=["Use the same task set and runtime environment"],
        parameters={"dataset": "fixture-v1", "trial_count": 3},
        success_criteria=["Pass the declared tests", "Record the measured cost"],
        prohibited_actions=["Deploy changes without review"],
        prohibited_operations=["deploy"],
        permitted_operations=["ingest-evidence", "run-tests", "compare-results"],
    )


def make_keypair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """Generate an in-memory test key pair."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def test_signed_directive_verifies_and_authorizes_allowlisted_operation() -> None:
    private_key, public_key = make_keypair()
    directive = make_directive()
    directive.sign(private_key, "test-reviewer")

    assert directive.verify(public_key)
    directive.authorize_operation("run-tests", public_key)
    assert len(directive.directive_digest) == 64


def test_unsigned_directive_cannot_authorize_operations() -> None:
    _, public_key = make_keypair()
    directive = make_directive()
    with pytest.raises(PermissionError, match="signature is missing or invalid"):
        directive.authorize_operation("run-tests", public_key)


def test_non_allowlisted_operation_is_denied() -> None:
    private_key, public_key = make_keypair()
    directive = make_directive()
    directive.sign(private_key, "test-reviewer")
    with pytest.raises(PermissionError, match="not explicitly permitted"):
        directive.authorize_operation("write-to-production", public_key)


def test_explicitly_prohibited_operation_is_denied() -> None:
    private_key, public_key = make_keypair()
    directive = make_directive()
    directive.sign(private_key, "test-reviewer")
    with pytest.raises(PermissionError, match="is prohibited"):
        directive.authorize_operation("deploy", public_key)


def test_any_signed_field_change_invalidates_signature() -> None:
    private_key, public_key = make_keypair()
    directive = make_directive()
    directive.sign(private_key, "test-reviewer")
    directive.constraints.append("Ignore prior constraints")
    assert not directive.verify(public_key)


def test_payload_digest_is_stable_for_identical_directives() -> None:
    first = make_directive()
    second = make_directive()
    assert first.directive_digest == second.directive_digest


def test_naive_timestamps_are_rejected() -> None:
    with pytest.raises(ValidationError, match="must include a timezone"):
        HumanDirectiveRecord(
            directive_id="hdr-naive-time",
            timestamp=datetime(2026, 10, 22, 12, 0, 0),
            objectives=["compare"],
            success_criteria=["tested"],
        )


def test_duplicate_or_blank_permissions_are_rejected() -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        HumanDirectiveRecord(
            directive_id="hdr-duplicate",
            objectives=["compare"],
            success_criteria=["tested"],
            permitted_operations=["run-tests", "run-tests"],
        )
    with pytest.raises(ValidationError, match="must not be blank"):
        HumanDirectiveRecord(
            directive_id="hdr-blank",
            objectives=["compare"],
            success_criteria=["tested"],
            permitted_operations=[" "],
        )
