"""Thalos Prime NEXUS Core v1 — Attest Package.

Exports the public API of the attest sub-package: key management, manifest
signing/verification, and SBOM generation.
"""

from __future__ import annotations

from thalos_nexus.attest.sbom import SbomGenerator
from thalos_nexus.attest.signing import (
    KeyPair,
    load_or_generate_keypair,
    sign_manifest,
    verify_manifest_signature,
)

__all__: list[str] = [
    "KeyPair",
    "SbomGenerator",
    "load_or_generate_keypair",
    "sign_manifest",
    "verify_manifest_signature",
]
