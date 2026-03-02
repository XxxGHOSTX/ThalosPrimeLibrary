"""Thalos Prime NEXUS Core v1 — Artifact Store.

Manages writing, digesting, and referencing run artifacts (JSON, text, binary)
within a deterministic run directory.

Control Plane boundary: file I/O only — no lifecycle coordination logic.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ArtifactStore:
    """Manages artifact files within a deterministic run directory.

    All files are written to *run_dir*.  Digest operations use SHA-256.

    Args:
        run_dir: Directory under which all artifacts are stored.  The
                 directory is created on construction if it does not exist.

    """

    def __init__(self, run_dir: Path) -> None:
        """Initialise the store and create *run_dir* if necessary."""
        self._run_dir = run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("ArtifactStore initialised at %s", run_dir)

    @property
    def run_dir(self) -> Path:
        """Return the run directory path."""
        return self._run_dir

    def write_json(self, name: str, data: dict[str, Any]) -> tuple[Path, str]:
        """Write *data* as indented JSON to run_dir/name.

        Args:
            name: File name (relative to run_dir).
            data: JSON-serialisable mapping.

        Returns:
            Tuple of (absolute Path, sha256 hex digest).

        """
        path = self._run_dir / name
        raw = json.dumps(data, indent=2, sort_keys=True).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        logger.debug("Wrote JSON artifact %s (%s)", path, digest)
        return path, digest

    def write_text(self, name: str, text: str) -> tuple[Path, str]:
        """Write *text* as UTF-8 to run_dir/name.

        Args:
            name: File name (relative to run_dir).
            text: Text content.

        Returns:
            Tuple of (absolute Path, sha256 hex digest).

        """
        path = self._run_dir / name
        raw = text.encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        logger.debug("Wrote text artifact %s (%s)", path, digest)
        return path, digest

    def write_bytes(self, name: str, data: bytes) -> tuple[Path, str]:
        """Write raw *data* to run_dir/name.

        Args:
            name: File name (relative to run_dir).
            data: Raw bytes content.

        Returns:
            Tuple of (absolute Path, sha256 hex digest).

        """
        path = self._run_dir / name
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        logger.debug("Wrote bytes artifact %s (%s)", path, digest)
        return path, digest

    def digest_file(self, path: Path) -> str:
        """Return the SHA-256 hex digest of the file at *path*.

        Args:
            path: Absolute or relative path to the file to digest.

        Returns:
            64-character lowercase hexadecimal SHA-256 digest.

        Raises:
            FileNotFoundError: If *path* does not exist.

        """
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest()

    def make_artifact_ref(self, name: str, path: Path, sha256: str) -> dict[str, str]:
        """Build an artifact reference dict suitable for repro_manifest.

        The ``path`` value in the returned dict is relative to the run
        directory so that manifests remain portable.

        Args:
            name: Logical artifact name (used for logging only).
            path: Absolute path to the artifact file.
            sha256: Pre-computed SHA-256 digest of the artifact.

        Returns:
            ``{"path": "<relative_path>", "sha256": "<hex>"}``

        """
        try:
            rel = path.relative_to(self._run_dir)
            rel_str = str(rel)
        except ValueError:
            rel_str = str(path)
        logger.debug("ArtifactRef %s: path=%s sha256=%s", name, rel_str, sha256)
        return {"path": rel_str, "sha256": sha256}
