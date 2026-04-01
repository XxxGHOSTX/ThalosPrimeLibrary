"""Deterministic PRP-based indexing for ThalosPrime Library.

Data Plane module: provides content-to-coordinate mapping using an
AES-128-ECB based keyed PRP. Coordinate tuples are deterministically
derived from content hashes. This module has NO lifecycle orchestration.

Coordinate scheme:
  hexagon: bytes[0:2]  -> int (0-65535)
  wall:    bytes[2:3]  -> int (0-255)
  shelf:   bytes[3:4]  -> int (0-255)
  volume:  bytes[4:6]  -> int (0-65535)
  page:    bytes[6:8]  -> int (0-65535)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from enum import StrEnum

from cryptography.hazmat.primitives.ciphers import (
    Cipher,
    algorithms,
    modes,
)

logger = logging.getLogger(__name__)

# AES-128 requires exactly 16-byte keys and 16-byte input blocks
_AES_KEY_SIZE: int = 16
_AES_BLOCK_SIZE: int = 16


@dataclass(frozen=True)
class Coordinate:
    """An immutable 5-tuple address within the Library of Babel coordinate space.

    Each dimension maps to a specific byte range of an AES-128-ECB PRP output
    over a SHA-256 content hash (first 8 bytes used).

    Attributes:
        hexagon: 16-bit hexagon index derived from bytes[0:2] (0-65535).
        wall: 8-bit wall index derived from bytes[2:3] (0-255).
        shelf: 8-bit shelf index derived from bytes[3:4] (0-255).
        volume: 16-bit volume index derived from bytes[4:6] (0-65535).
        page: 16-bit page index derived from bytes[6:8] (0-65535).

    """

    hexagon: int
    wall: int
    shelf: int
    volume: int
    page: int

    def to_tuple(self) -> tuple[int, int, int, int, int]:
        """Return the coordinate as a plain 5-tuple.

        Returns:
            ``(hexagon, wall, shelf, volume, page)`` as plain Python ints.

        """
        return (self.hexagon, self.wall, self.shelf, self.volume, self.page)

    def to_hex_str(self) -> str:
        """Return the coordinate encoded as a 16-character lowercase hex string.

        The encoding packs the 5 dimensions into 8 bytes:
        ``hexagon`` (2 B) + ``wall`` (1 B) + ``shelf`` (1 B) +
        ``volume`` (2 B) + ``page`` (2 B).

        Returns:
            16-character lowercase hex string uniquely identifying this coordinate.

        """
        return (
            f"{self.hexagon:04x}"
            f"{self.wall:02x}"
            f"{self.shelf:02x}"
            f"{self.volume:04x}"
            f"{self.page:04x}"
        )


class CoordinateType(StrEnum):
    """The semantic role of a coordinate within an ArtifactCoordinates bundle.

    Members:
        IDENTITY: Derived from the artifact ID — uniquely identifies the artifact.
        SEMANTIC: Derived from content — groups semantically similar artifacts.
        PROVENANCE: Derived from the provenance hash — links lineage clusters.
        VERSION: Derived from version and artifact ID — tracks revision history.
        TRUST_STATE: Derived from trust value and artifact ID — encodes trust level.

    """

    IDENTITY = "identity"
    SEMANTIC = "semantic"
    PROVENANCE = "provenance"
    VERSION = "version"
    TRUST_STATE = "trust_state"


@dataclass
class ArtifactCoordinates:
    """A complete set of five typed coordinates for a single artifact.

    Each coordinate is computed by a different PRP input, giving independent
    address axes for identity, semantic content, provenance lineage, version,
    and trust state.

    Attributes:
        identity: Coordinate derived from the artifact ID.
        semantic: Coordinate derived from the artifact content.
        provenance: Coordinate derived from the provenance hash.
        version: Coordinate derived from the version string and artifact ID.
        trust_state: Coordinate derived from the quantised trust value and artifact ID.

    """

    identity: Coordinate
    semantic: Coordinate
    provenance: Coordinate
    version: Coordinate
    trust_state: Coordinate


class PrpIndexer:
    """Deterministic PRP-based content indexer using AES-128-ECB.

    Maps arbitrary string content to :class:`Coordinate` tuples through a
    two-step pipeline: SHA-256 content hash (first 16 bytes) → AES-128-ECB
    encryption → coordinate extraction from the first 8 bytes of ciphertext.

    Because the PRP is keyed, two indexers with different keys produce
    independent, unrelated address spaces.
    """

    def __init__(self, key: bytes) -> None:
        """Initialise the PRP indexer with an AES-128 key.

        Args:
            key: Exactly 16-byte AES-128 key for the PRP permutation.

        Raises:
            ValueError: When *key* is not exactly 16 bytes.

        """
        if len(key) != _AES_KEY_SIZE:
            msg = f"key must be exactly {_AES_KEY_SIZE} bytes, got {len(key)}"
            raise ValueError(msg)
        self._key = key

    def _compute_hash(self, content: str) -> bytes:
        """Compute the first 16 bytes of the SHA-256 digest of *content*.

        Args:
            content: UTF-8 string to hash.

        Returns:
            First 16 bytes of the SHA-256 digest.

        """
        return hashlib.sha256(content.encode("utf-8")).digest()[:_AES_BLOCK_SIZE]

    def _prp_transform(self, data: bytes) -> bytes:
        """Apply AES-128-ECB encryption to *data* as the PRP permutation.

        Args:
            data: Exactly 16 bytes of input (one AES block).

        Returns:
            16 bytes of AES-128-ECB ciphertext.

        Raises:
            ValueError: When *data* is not exactly 16 bytes.

        """
        if len(data) != _AES_BLOCK_SIZE:
            msg = f"PRP input must be exactly {_AES_BLOCK_SIZE} bytes, got {len(data)}"
            raise ValueError(msg)
        cipher = Cipher(
            algorithms.AES(self._key),
            # ECB mode is intentional: this is a PRP (Pseudo-Random Permutation)
            # used as a deterministic bijection over hash space, NOT an encryption
            # scheme for sensitive data. No plaintext/ciphertext patterns exist
            # because each 16-byte input is an independent SHA-256 hash slice.
            modes.ECB(),  # noqa: S305
        )
        encryptor = cipher.encryptor()
        result: bytes = encryptor.update(data) + encryptor.finalize()
        return result

    def _bytes_to_coordinate(self, data: bytes) -> Coordinate:
        """Parse the first 8 bytes of *data* into a :class:`Coordinate`.

        Byte layout matches the module-level coordinate scheme:
        ``bytes[0:2]`` → hexagon, ``bytes[2:3]`` → wall,
        ``bytes[3:4]`` → shelf, ``bytes[4:6]`` → volume,
        ``bytes[6:8]`` → page.

        Args:
            data: At least 8 bytes of PRP output.

        Returns:
            A :class:`Coordinate` populated from the first 8 bytes.

        """
        hexagon = int.from_bytes(data[0:2], "big")
        wall = int.from_bytes(data[2:3], "big")
        shelf = int.from_bytes(data[3:4], "big")
        volume = int.from_bytes(data[4:6], "big")
        page = int.from_bytes(data[6:8], "big")
        return Coordinate(
            hexagon=hexagon,
            wall=wall,
            shelf=shelf,
            volume=volume,
            page=page,
        )

    def index(self, content: str) -> Coordinate:
        """Map *content* to a deterministic :class:`Coordinate`.

        Full pipeline: ``content`` → SHA-256 hash (first 16 B) →
        AES-128-ECB PRP → coordinate extraction (first 8 B).

        Args:
            content: UTF-8 string to index.

        Returns:
            A deterministic :class:`Coordinate` for *content* under this key.

        """
        h = self._compute_hash(content)
        prp_out = self._prp_transform(h)
        return self._bytes_to_coordinate(prp_out)

    def index_artifact(
        self,
        artifact_id: str,
        content: str,
        provenance_hash: str,
        version: int,
        trust_value: float,
    ) -> ArtifactCoordinates:
        """Compute all five typed coordinates for a single artifact.

        Each coordinate is derived by hashing a different semantic key:

        - **IDENTITY**: ``hash(artifact_id)``
        - **SEMANTIC**: ``hash(content)``
        - **PROVENANCE**: ``hash(provenance_hash)``
        - **VERSION**: ``hash(f"v{version}:{artifact_id}")``
        - **TRUST_STATE**: ``hash(f"t{int(trust_value*1000)}:{artifact_id}")``

        Args:
            artifact_id: Unique artifact identifier (e.g. SHA-256 hex digest).
            content: Raw artifact content string.
            provenance_hash: Hex hash representing provenance lineage.
            version: Integer artifact version number.
            trust_value: Float trust score in ``[0.0, 1.0]``; quantised to
                integer thousandths before hashing.

        Returns:
            An :class:`ArtifactCoordinates` with all five typed coordinates
            populated.

        """
        identity = self.index(artifact_id)
        semantic = self.index(content)
        provenance = self.index(provenance_hash)
        version_coord = self.index(f"v{version}:{artifact_id}")
        trust_coord = self.index(f"t{int(trust_value * 1000)}:{artifact_id}")
        return ArtifactCoordinates(
            identity=identity,
            semantic=semantic,
            provenance=provenance,
            version=version_coord,
            trust_state=trust_coord,
        )


__all__ = [
    "ArtifactCoordinates",
    "Coordinate",
    "CoordinateType",
    "PrpIndexer",
]
