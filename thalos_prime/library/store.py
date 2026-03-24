"""Local filesystem-backed library artifact store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from thalos_prime.library.models import LibraryArtifact
from thalos_prime.storage.provider import get_storage_base_path


class LibraryStoreProtocol(Protocol):
    """Protocol for library artifact persistence backends."""

    def save(self, artifact: LibraryArtifact) -> LibraryArtifact:
        """Persist an artifact, returning it.

        Args:
            artifact: LibraryArtifact to persist.

        Returns:
            The persisted artifact (same object or deduplicated version).

        """
        ...

    def get(self, artifact_id: str) -> LibraryArtifact | None:
        """Return an artifact by its content-addressed ID, or None.

        Args:
            artifact_id: SHA-256 hex content address.

        Returns:
            LibraryArtifact if found, else None.

        """
        ...

    def list_ids(self) -> list[str]:
        """List all stored artifact IDs.

        Returns:
            Sorted list of artifact content addresses.

        """
        ...


class LocalLibraryStore:
    """Saves library artifacts as JSON files, deduplicated by content hash.

    Each artifact is stored at ``base_path/library/{artifact_id}.json``.
    Because the file name is the SHA-256 hash of the content, identical
    content always maps to the same file (automatic deduplication).
    """

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize the store with an optional custom base path.

        Args:
            base_path: Root directory for artifact storage. Uses the default
                from get_storage_base_path() if not provided.

        """
        self._base = (base_path if base_path is not None else get_storage_base_path()) / "library"
        self._base.mkdir(parents=True, exist_ok=True)

    def _artifact_path(self, artifact_id: str) -> Path:
        """Return the JSON file path for a specific artifact.

        Args:
            artifact_id: SHA-256 hex content address.

        Returns:
            Path to the artifact's JSON file.

        """
        return self._base / f"{artifact_id}.json"

    def save(self, artifact: LibraryArtifact) -> LibraryArtifact:
        """Persist an artifact to disk, deduplicating by content hash.

        If an artifact with the same ID already exists, it is overwritten
        (idempotent — same content produces the same file).

        Args:
            artifact: LibraryArtifact to persist.

        Returns:
            The persisted artifact.

        """
        path = self._artifact_path(artifact.id)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(artifact.to_dict(), fh, ensure_ascii=False, sort_keys=True)
        return artifact

    def get(self, artifact_id: str) -> LibraryArtifact | None:
        """Return an artifact by ID, or None if not found.

        Args:
            artifact_id: SHA-256 hex content address to look up.

        Returns:
            Deserialized LibraryArtifact, or None if not stored.

        """
        path = self._artifact_path(artifact_id)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as fh:
            data: dict[str, object] = json.load(fh)
        return LibraryArtifact.from_dict(data)

    def list_ids(self) -> list[str]:
        """List all stored artifact IDs.

        Returns:
            Sorted list of artifact content addresses (filenames without .json).

        """
        if not self._base.exists():
            return []
        return sorted(p.stem for p in self._base.glob("*.json"))


__all__ = ["LibraryStoreProtocol", "LocalLibraryStore"]
