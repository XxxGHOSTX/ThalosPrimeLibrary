"""Thalos Prime NEXUS Core v1 — ed25519 Signing.

Provides :class:`KeyPair` for generating, loading, saving, and using ed25519
keys, plus helpers for signing and verifying repro_manifest payloads.

Uses the ``cryptography`` package (cross-platform).

Control Plane boundary: cryptographic operations only — no I/O beyond
PEM file read/write.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

logger = logging.getLogger(__name__)


class KeyPair:
    """Wraps an ed25519 private/public key pair.

    Use :meth:`generate` or :meth:`load` as constructors rather than
    calling ``__init__`` directly.
    """

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        """Initialise from an existing *private_key* object."""
        self._private_key: Ed25519PrivateKey = private_key
        self._public_key: Ed25519PublicKey = private_key.public_key()

    @classmethod
    def generate(cls) -> KeyPair:
        """Generate a new random ed25519 key pair.

        Returns:
            A fresh :class:`KeyPair`.

        """
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def load(cls, path: Path) -> KeyPair:
        """Load a key pair from PEM files at *path*/private.pem and *path*/public.pem.

        Args:
            path: Directory containing ``private.pem`` and ``public.pem``.

        Returns:
            :class:`KeyPair` loaded from the PEM files.

        Raises:
            FileNotFoundError: If the PEM files do not exist.
            ValueError: If the key files cannot be parsed.

        """
        private_pem = (path / "private.pem").read_bytes()
        private_key = serialization.load_pem_private_key(private_pem, password=None)
        if not isinstance(private_key, Ed25519PrivateKey):
            raise TypeError(f"Expected Ed25519PrivateKey, got {type(private_key)}")
        return cls(private_key)

    def save(self, path: Path) -> None:
        """Save the key pair to *path*/private.pem and *path*/public.pem.

        Args:
            path: Directory to write PEM files into.  Created if absent.

        """
        path.mkdir(parents=True, exist_ok=True)
        private_bytes = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        (path / "private.pem").write_bytes(private_bytes)

        public_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        (path / "public.pem").write_bytes(public_bytes)
        logger.debug("Saved key pair to %s", path)

    def sign(self, data: bytes) -> bytes:
        """Sign *data* and return the raw 64-byte signature.

        Args:
            data: Bytes to sign.

        Returns:
            64-byte ed25519 signature.

        """
        return self._private_key.sign(data)

    def public_key_hex(self) -> str:
        """Return the lowercase hex-encoded raw 32-byte public key.

        Returns:
            64-character lowercase hexadecimal string.

        """
        raw = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return raw.hex()

    def signature_hex(self, data: bytes) -> str:
        """Return the lowercase hex-encoded ed25519 signature of *data*.

        Args:
            data: Bytes to sign.

        Returns:
            128-character lowercase hexadecimal string.

        """
        return self.sign(data).hex()

    @staticmethod
    def verify(data: bytes, signature_hex: str, public_key_hex: str) -> bool:
        """Verify an ed25519 signature.

        Args:
            data: Original signed payload.
            signature_hex: Hex-encoded signature (128 hex chars).
            public_key_hex: Hex-encoded raw public key (64 hex chars).

        Returns:
            ``True`` if the signature is valid, ``False`` otherwise.

        """
        from cryptography.exceptions import InvalidSignature

        try:
            raw_pub = bytes.fromhex(public_key_hex)
            raw_sig = bytes.fromhex(signature_hex)
            pub_key = Ed25519PublicKey.from_public_bytes(raw_pub)
            pub_key.verify(raw_sig, data)
        except (InvalidSignature, ValueError):
            return False
        return True


def load_or_generate_keypair(key_dir: Path) -> KeyPair:
    """Load an existing key pair or generate and persist a new one.

    If ``key_dir/private.pem`` and ``key_dir/public.pem`` both exist, they
    are loaded.  Otherwise a new key pair is generated, saved, and returned.

    Args:
        key_dir: Directory containing (or to receive) PEM key files.

    Returns:
        A :class:`KeyPair` loaded from or saved to *key_dir*.

    """
    private_pem = key_dir / "private.pem"
    public_pem = key_dir / "public.pem"
    if private_pem.exists() and public_pem.exists():
        kp = KeyPair.load(key_dir)
        logger.debug("Loaded existing key pair from %s", key_dir)
        return kp
    kp = KeyPair.generate()
    kp.save(key_dir)
    logger.debug("Generated new key pair at %s", key_dir)
    return kp


def sign_manifest(manifest: dict[str, Any], key_pair: KeyPair) -> dict[str, Any]:
    """Attach an ed25519 signature to *manifest*.

    The signature covers the canonical JSON of the manifest *without* any
    existing ``"signature"`` field.

    Args:
        manifest: Manifest dictionary (must not contain a ``"signature"`` key).
        key_pair: Key pair used for signing.

    Returns:
        A new dictionary equal to *manifest* with the ``"signature"`` field
        added.

    """
    from thalos_nexus.nucleus.determinism import canonical_json

    manifest_clean = {k: v for k, v in manifest.items() if k != "signature"}
    payload = canonical_json(manifest_clean)
    sig_hex = key_pair.signature_hex(payload)
    signed: dict[str, Any] = {
        **manifest_clean,
        "signature": {
            "algorithm": "ed25519",
            "public_key_hex": key_pair.public_key_hex(),
            "signature_hex": sig_hex,
        },
    }
    return signed


def verify_manifest_signature(manifest: dict[str, Any]) -> bool:
    """Verify the ed25519 signature embedded in *manifest*.

    Args:
        manifest: Manifest dictionary including a ``"signature"`` field.

    Returns:
        ``True`` if the signature is valid, ``False`` if absent or invalid.

    """
    from thalos_nexus.nucleus.determinism import canonical_json

    sig_block = manifest.get("signature")
    if not isinstance(sig_block, dict):
        return False
    public_key_hex: str = sig_block.get("public_key_hex", "")
    signature_hex: str = sig_block.get("signature_hex", "")
    manifest_clean = {k: v for k, v in manifest.items() if k != "signature"}
    payload = canonical_json(manifest_clean)
    return KeyPair.verify(payload, signature_hex, public_key_hex)
