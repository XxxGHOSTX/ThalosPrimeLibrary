"""Tests for the Artifact Schema subsystem.

Covers DerivationStep, ProvenanceNode, FacsBundle, Artifact, and GenesisLock.
All tests use deterministic inputs and fixed timestamps for reproducibility.
"""

from __future__ import annotations

import hashlib

import pytest

from thalos_prime.artifacts.schema import (
    Artifact,
    DerivationStep,
    FacsBundle,
    GenesisLock,
    ProvenanceNode,
    ValidationStatus,
)

# ---------------------------------------------------------------------------
# Fixed test constants
# ---------------------------------------------------------------------------
_TS = 1_700_000_000_000_000_000  # Fixed nanosecond timestamp
_KEY = b"\x00" * 16  # 16-byte HMAC key (deterministic)


# ===========================================================================
# DerivationStep
# ===========================================================================


class TestDerivationStep:
    def test_fields_round_trip(self) -> None:
        step = DerivationStep(
            step_id="step-abc",
            operation="tokenise",
            input_ids=["id-1", "id-2"],
            output_id="id-3",
            timestamp_ns=_TS,
            config_hash="a" * 64,
        )
        assert step.step_id == "step-abc"
        assert step.operation == "tokenise"
        assert step.input_ids == ["id-1", "id-2"]
        assert step.output_id == "id-3"
        assert step.timestamp_ns == _TS
        assert step.config_hash == "a" * 64

    def test_serialisation_round_trip(self) -> None:
        step = DerivationStep(
            step_id="s1",
            operation="embed",
            input_ids=["a"],
            output_id="b",
            timestamp_ns=_TS,
            config_hash="c" * 64,
        )
        data = step.model_dump()
        restored = DerivationStep.model_validate(data)
        assert restored == step

    def test_empty_input_ids(self) -> None:
        step = DerivationStep(
            step_id="s0",
            operation="genesis",
            input_ids=[],
            output_id="gen-0",
            timestamp_ns=0,
            config_hash="0" * 64,
        )
        assert step.input_ids == []


# ===========================================================================
# ProvenanceNode
# ===========================================================================


class TestProvenanceNode:
    def test_defaults_and_fields(self) -> None:
        node = ProvenanceNode(
            node_id="n1",
            artifact_id="art-1",
            parent_ids=[],
            derivation_steps=[],
            created_at_ns=_TS,
            version=1,
        )
        assert node.source_uri is None
        assert node.version == 1

    def test_with_source_uri(self) -> None:
        node = ProvenanceNode(
            node_id="n2",
            artifact_id="art-2",
            parent_ids=["n1"],
            derivation_steps=[],
            source_uri="https://example.com/data",
            created_at_ns=_TS,
            version=2,
        )
        assert node.source_uri == "https://example.com/data"
        assert node.parent_ids == ["n1"]

    def test_with_derivation_steps(self) -> None:
        step = DerivationStep(
            step_id="s1",
            operation="transform",
            input_ids=["x"],
            output_id="y",
            timestamp_ns=_TS,
            config_hash="f" * 64,
        )
        node = ProvenanceNode(
            node_id="n3",
            artifact_id="art-3",
            parent_ids=[],
            derivation_steps=[step],
            created_at_ns=_TS,
            version=1,
        )
        assert len(node.derivation_steps) == 1
        assert node.derivation_steps[0].step_id == "s1"

    def test_serialisation_round_trip(self) -> None:
        node = ProvenanceNode(
            node_id="n4",
            artifact_id="art-4",
            parent_ids=["n3"],
            derivation_steps=[],
            source_uri="uri://test",
            created_at_ns=_TS,
            version=3,
        )
        data = node.model_dump()
        restored = ProvenanceNode.model_validate(data)
        assert restored == node


# ===========================================================================
# FacsBundle
# ===========================================================================


class TestFacsBundle:
    def test_defaults(self) -> None:
        bundle = FacsBundle()
        assert bundle.flags == {}
        assert bundle.annotations == {}
        assert bundle.contradiction_map == {}
        assert bundle.suspension_log == []
        assert bundle.schema_version == 1

    def test_fields_populated(self) -> None:
        bundle = FacsBundle(
            flags={"disputed": True, "verified": False},
            annotations={"author": "thalos"},
            contradiction_map={"art-1": ["art-2", "art-3"]},
            suspension_log=[{"reason": "test", "artifact_id": "art-1", "timestamp_ns": "0"}],
        )
        assert bundle.flags["disputed"] is True
        assert bundle.flags["verified"] is False
        assert bundle.annotations["author"] == "thalos"
        assert bundle.contradiction_map["art-1"] == ["art-2", "art-3"]
        assert len(bundle.suspension_log) == 1

    def test_serialisation_round_trip(self) -> None:
        bundle = FacsBundle(flags={"ok": True})
        data = bundle.model_dump()
        restored = FacsBundle.model_validate(data)
        assert restored == bundle


# ===========================================================================
# Artifact
# ===========================================================================


class TestArtifact:
    def test_create_deterministic(self) -> None:
        a1 = Artifact.create(
            content="Hello World",
            source_uris=["uri://a"],
            timestamp_ns=_TS,
        )
        a2 = Artifact.create(
            content="Hello World",
            source_uris=["uri://a"],
            timestamp_ns=_TS,
        )
        assert a1.artifact_id == a2.artifact_id
        assert a1.content_hash == a2.content_hash
        assert a1.canonical_form == a2.canonical_form

    def test_create_content_hash(self) -> None:
        content = "test content"
        artifact = Artifact.create(content=content, source_uris=[], timestamp_ns=_TS)
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert artifact.content_hash == expected_hash

    def test_create_artifact_id_from_canonical(self) -> None:
        content = "  Hello   World  "
        artifact = Artifact.create(content=content, source_uris=[], timestamp_ns=_TS)
        canonical = "hello world"
        expected_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert artifact.canonical_form == canonical
        assert artifact.artifact_id == expected_id

    def test_create_whitespace_normalisation(self) -> None:
        a1 = Artifact.create(content="foo  bar", source_uris=[], timestamp_ns=_TS)
        a2 = Artifact.create(content="foo bar", source_uris=[], timestamp_ns=_TS)
        assert a1.canonical_form == a2.canonical_form
        assert a1.artifact_id == a2.artifact_id

    def test_create_case_insensitive(self) -> None:
        a1 = Artifact.create(content="Hello", source_uris=[], timestamp_ns=_TS)
        a2 = Artifact.create(content="HELLO", source_uris=[], timestamp_ns=_TS)
        assert a1.artifact_id == a2.artifact_id

    def test_create_default_metadata(self) -> None:
        artifact = Artifact.create(content="x", source_uris=[], timestamp_ns=_TS)
        assert artifact.metadata == {}

    def test_create_with_metadata(self) -> None:
        artifact = Artifact.create(
            content="x",
            source_uris=[],
            metadata={"k": "v"},
            timestamp_ns=_TS,
        )
        assert artifact.metadata["k"] == "v"

    def test_create_defaults_timestamp(self) -> None:
        artifact = Artifact.create(content="x", source_uris=[])
        assert artifact.timestamp_ns > 0

    def test_default_validation_status(self) -> None:
        artifact = Artifact.create(content="y", source_uris=[], timestamp_ns=_TS)
        assert artifact.validation_status is ValidationStatus.PENDING

    def test_serialisation_round_trip(self) -> None:
        artifact = Artifact.create(
            content="round trip test",
            source_uris=["s://x"],
            timestamp_ns=_TS,
        )
        data = artifact.model_dump()
        restored = Artifact.model_validate(data)
        assert restored.artifact_id == artifact.artifact_id
        assert restored.content_hash == artifact.content_hash

    def test_optional_provenance_none(self) -> None:
        artifact = Artifact.create(content="no prov", source_uris=[], timestamp_ns=_TS)
        assert artifact.provenance is None

    def test_optional_facs_none(self) -> None:
        artifact = Artifact.create(content="no facs", source_uris=[], timestamp_ns=_TS)
        assert artifact.facs is None

    def test_optional_signature_none(self) -> None:
        artifact = Artifact.create(content="no sig", source_uris=[], timestamp_ns=_TS)
        assert artifact.signature is None

    def test_temporal_scope_optional(self) -> None:
        artifact = Artifact.create(content="scoped", source_uris=[], timestamp_ns=_TS)
        assert artifact.temporal_scope is None

    def test_schema_and_version_defaults(self) -> None:
        artifact = Artifact.create(content="v", source_uris=[], timestamp_ns=_TS)
        assert artifact.version == 1
        assert artifact.schema_version == 1


# ===========================================================================
# GenesisLock
# ===========================================================================


class TestGenesisLock:
    def test_sign_returns_hex_string(self) -> None:
        artifact = Artifact.create(content="sign me", source_uris=[], timestamp_ns=_TS)
        gl = GenesisLock(key=_KEY)
        sig = gl.sign(artifact)
        assert isinstance(sig, str)
        # HMAC-SHA256 produces 32 bytes = 64 hex chars
        assert len(sig) == 64

    def test_sign_is_deterministic(self) -> None:
        artifact = Artifact.create(content="deterministic", source_uris=[], timestamp_ns=_TS)
        gl = GenesisLock(key=_KEY)
        assert gl.sign(artifact) == gl.sign(artifact)

    def test_verify_valid_signature(self) -> None:
        artifact = Artifact.create(content="verify me", source_uris=[], timestamp_ns=_TS)
        gl = GenesisLock(key=_KEY)
        sig = gl.sign(artifact)
        assert gl.verify(artifact, sig) is True

    def test_verify_invalid_signature(self) -> None:
        artifact = Artifact.create(content="verify me", source_uris=[], timestamp_ns=_TS)
        gl = GenesisLock(key=_KEY)
        assert gl.verify(artifact, "deadbeef" * 8) is False

    def test_different_keys_produce_different_signatures(self) -> None:
        artifact = Artifact.create(content="keys differ", source_uris=[], timestamp_ns=_TS)
        gl1 = GenesisLock(key=b"\x00" * 16)
        gl2 = GenesisLock(key=b"\xff" * 16)
        assert gl1.sign(artifact) != gl2.sign(artifact)

    def test_verify_wrong_artifact(self) -> None:
        a1 = Artifact.create(content="artifact one", source_uris=[], timestamp_ns=_TS)
        a2 = Artifact.create(content="artifact two", source_uris=[], timestamp_ns=_TS)
        gl = GenesisLock(key=_KEY)
        sig = gl.sign(a1)
        assert gl.verify(a2, sig) is False

    def test_signature_changes_on_status_change(self) -> None:
        artifact = Artifact.create(content="status change", source_uris=[], timestamp_ns=_TS)
        gl = GenesisLock(key=_KEY)
        sig_pending = gl.sign(artifact)
        accepted = artifact.model_copy(
            update={"validation_status": ValidationStatus.ACCEPTED}
        )
        sig_accepted = gl.sign(accepted)
        assert sig_pending != sig_accepted

    def test_genesis_lock_with_various_key_lengths(self) -> None:
        artifact = Artifact.create(content="key len", source_uris=[], timestamp_ns=_TS)
        for length in [16, 32, 64]:
            gl_trimmed = GenesisLock(
                key=(bytes(range(length % 256)) * (length // 256 + 1))[:length]
            )
            sig = gl_trimmed.sign(artifact)
            assert isinstance(sig, str)
            assert len(sig) == 64

    def test_validation_status_enum_values(self) -> None:
        assert ValidationStatus.PENDING.value == "pending"
        assert ValidationStatus.ACCEPTED.value == "accepted"
        assert ValidationStatus.DISPUTED.value == "disputed"
        assert ValidationStatus.REJECTED.value == "rejected"


# ===========================================================================
# ValidationStatus
# ===========================================================================


class TestValidationStatus:
    def test_all_members(self) -> None:
        members = set(ValidationStatus)
        assert ValidationStatus.PENDING in members
        assert ValidationStatus.ACCEPTED in members
        assert ValidationStatus.DISPUTED in members
        assert ValidationStatus.REJECTED in members

    def test_is_str(self) -> None:
        assert isinstance(ValidationStatus.PENDING, str)

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (ValidationStatus.PENDING, "pending"),
            (ValidationStatus.ACCEPTED, "accepted"),
            (ValidationStatus.DISPUTED, "disputed"),
            (ValidationStatus.REJECTED, "rejected"),
        ],
    )
    def test_string_values(self, status: ValidationStatus, expected: str) -> None:
        assert status == expected
