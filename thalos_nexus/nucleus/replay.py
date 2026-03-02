"""Thalos Prime NEXUS Core v1 — Replay Verifier.

Provides :class:`ReplayVerifier` which validates a repro_manifest against
its associated artifacts: file existence, SHA-256 integrity, event-log hash
chain, and optional ed25519 signature.

Control Plane boundary: read-only verification — no write side-effects.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "repro_manifest.schema.json"


def _load_schema() -> dict[str, Any]:
    """Load the repro_manifest JSON Schema from the schemas directory."""
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


class ReplayVerifier:
    """Verifies that a repro_manifest leads to reproducible artifacts.

    All verification methods are pure read operations; no files are written
    or modified.
    """

    def verify_manifest(self, manifest_path: Path, artifacts_dir: Path) -> list[str]:
        """Verify artifact integrity and event-log chain for *manifest_path*.

        Steps performed:

        1. Load and JSON-Schema-validate ``repro_manifest.json``.
        2. For every artifact reference in ``manifest["artifacts"]``, confirm
           the file exists under *artifacts_dir* and its SHA-256 matches.
        3. Verify the event-log hash chain via :class:`~.determinism.EventLogVerifier`.

        Args:
            manifest_path: Path to the repro_manifest.json file.
            artifacts_dir: Root directory from which artifact relative paths
                           are resolved.

        Returns:
            A list of error strings.  An empty list means all checks passed.

        """
        from thalos_nexus.nucleus.artifacts import ArtifactStore
        from thalos_nexus.nucleus.determinism import EventLogVerifier

        errors: list[str] = []

        if not manifest_path.exists():
            return [f"Manifest not found: {manifest_path}"]

        try:
            manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return [f"Manifest JSON parse error: {exc}"]

        schema_errors = _validate_schema(manifest)
        errors.extend(schema_errors)

        artifacts: dict[str, Any] = manifest.get("artifacts", {})
        store = ArtifactStore(artifacts_dir)

        for artifact_name, ref in artifacts.items():
            if not isinstance(ref, dict):
                errors.append(f"Artifact '{artifact_name}': invalid reference (not an object)")
                continue
            rel_path: str = ref.get("path", "")
            expected_sha: str = ref.get("sha256", "")
            artifact_file = artifacts_dir / rel_path
            if not artifact_file.exists():
                errors.append(f"Artifact '{artifact_name}': file not found: {artifact_file}")
                continue
            actual_sha = store.digest_file(artifact_file)
            if actual_sha != expected_sha:
                errors.append(
                    f"Artifact '{artifact_name}': SHA-256 mismatch — "
                    f"expected={expected_sha!r} actual={actual_sha!r}"
                )
            if artifact_name == "event_log":
                chain_errors = EventLogVerifier().verify(artifact_file)
                errors.extend(f"Event log chain error: {ce}" for ce in chain_errors)

        return errors

    def verify_signature(self, manifest_path: Path, public_key_hex: str) -> list[str]:
        """Verify the ed25519 signature embedded in a repro_manifest.

        Args:
            manifest_path: Path to the signed repro_manifest.json file.
            public_key_hex: Hex-encoded ed25519 public key (64 hex chars).

        Returns:
            A list of error strings.  An empty list means the signature is valid.

        """
        from thalos_nexus.attest.signing import KeyPair

        errors: list[str] = []

        if not manifest_path.exists():
            return [f"Manifest not found: {manifest_path}"]

        try:
            manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return [f"Manifest JSON parse error: {exc}"]

        sig_block: dict[str, Any] | None = manifest.get("signature")
        if sig_block is None:
            return ["No signature block found in manifest"]

        sig_hex: str = sig_block.get("signature_hex", "")
        manifest_without_sig = {k: v for k, v in manifest.items() if k != "signature"}

        from thalos_nexus.nucleus.determinism import canonical_json

        payload = canonical_json(manifest_without_sig)

        ok = KeyPair.verify(payload, sig_hex, public_key_hex)
        if not ok:
            errors.append("Signature verification failed")

        return errors


def _validate_schema(manifest: dict[str, Any]) -> list[str]:
    """Validate *manifest* against the repro_manifest JSON Schema.

    Args:
        manifest: Loaded manifest dictionary.

    Returns:
        List of validation error strings (empty if valid).

    """
    try:
        import jsonschema

        schema = _load_schema()
        validator = jsonschema.Draft202012Validator(schema)
        return [str(e.message) for e in validator.iter_errors(manifest)]
    except ImportError:
        logger.warning("jsonschema not installed; skipping schema validation")
        return []
