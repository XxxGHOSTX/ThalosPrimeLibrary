"""Library artifact model — content-addressed immutable text/document artifacts."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from thalos_prime.execution_ir.hash import sha256_hex


@dataclass
class LibraryArtifact:
    """An immutable, content-addressed library artifact.

    The artifact's ``id`` is the SHA-256 hash of its content, providing
    automatic deduplication by content identity.

    Attributes:
        id: SHA-256 hex digest of content — the content address.
        artifact_type: Semantic type label (e.g. ``"text"``, ``"document"``).
        content: The raw text content of this artifact.
        metadata: Arbitrary key-value metadata.
        created_at: ISO 8601 UTC timestamp of creation.

    """

    id: str
    artifact_type: str
    content: str
    metadata: dict[str, object]
    created_at: str

    def to_dict(self) -> dict[str, object]:
        """Serialize this artifact to a JSON-safe dictionary.

        Returns:
            Dictionary representation of this artifact.

        """
        return {
            "id": self.id,
            "artifact_type": self.artifact_type,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> LibraryArtifact:
        """Deserialize an artifact from a dictionary produced by to_dict().

        Args:
            d: Dictionary in the format produced by to_dict().

        Returns:
            Reconstructed LibraryArtifact instance.

        """
        raw_meta = d.get("metadata", {})
        metadata: dict[str, object] = dict(raw_meta) if isinstance(raw_meta, dict) else {}
        return cls(
            id=str(d["id"]),
            artifact_type=str(d["artifact_type"]),
            content=str(d["content"]),
            metadata=metadata,
            created_at=str(d["created_at"]),
        )

    @classmethod
    def create(
        cls,
        content: str,
        artifact_type: str = "text",
        metadata: dict[str, object] | None = None,
    ) -> LibraryArtifact:
        """Create a new LibraryArtifact with a content-derived ID.

        The artifact's ID is the SHA-256 hex digest of the content string,
        ensuring identical content always produces the same artifact ID.

        Args:
            content: Raw text content for this artifact.
            artifact_type: Semantic type label (default ``"text"``).
            metadata: Optional metadata dictionary. Empty dict if None.

        Returns:
            New LibraryArtifact instance with id = SHA-256(content).

        """
        artifact_id = sha256_hex(content)
        return cls(
            id=artifact_id,
            artifact_type=artifact_type,
            content=content,
            metadata=metadata if metadata is not None else {},
            created_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )


__all__ = ["LibraryArtifact"]
