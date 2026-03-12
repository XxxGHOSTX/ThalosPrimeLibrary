"""SHA-256 artifact hasher for infra-synthesis.

Data Plane helper: produces a deterministic manifest of output files.
No lifecycle state; pure function surface.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_ENCODING = "utf-8"


class Hasher:
    """Computes SHA-256 digests for a collection of output files.

    Each call to :meth:`hash_artifacts` scans the given paths, hashes their
    content deterministically, and writes ``artifact_manifest.json`` into the
    output directory.
    """

    @staticmethod
    def sha256_file(path: Path) -> str:
        """Return the hex-encoded SHA-256 digest of *path*.

        Args:
            path: Path to an existing file.

        Returns:
            64-character lowercase hex string.

        Raises:
            FileNotFoundError: When *path* does not exist.
            OSError: When *path* cannot be read.

        """
        digest = hashlib.sha256()
        digest.update(path.read_bytes())
        return digest.hexdigest()

    def hash_artifacts(self, artifact_paths: list[Path], out_dir: Path) -> dict[str, str]:
        """Hash all *artifact_paths* and write ``artifact_manifest.json``.

        Args:
            artifact_paths: Files to hash (must exist).
            out_dir: Directory where ``artifact_manifest.json`` is written.

        Returns:
            Mapping of relative path string → SHA-256 hex digest.

        Raises:
            FileNotFoundError: When any artifact path does not exist.

        """
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest: dict[str, str] = {}

        for ap in sorted(artifact_paths):
            rel = str(ap.relative_to(out_dir)) if ap.is_relative_to(out_dir) else ap.name
            digest = self.sha256_file(ap)
            manifest[rel] = digest
            logger.debug("Hashed '%s' -> %s", rel, digest)

        manifest_data: dict[str, Any] = {"artifacts": manifest}
        manifest_path = out_dir / "artifact_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_data, indent=2, sort_keys=True), encoding=_ENCODING
        )
        logger.info("Wrote artifact_manifest.json with %d entries", len(manifest))
        return manifest


__all__ = ["Hasher"]
