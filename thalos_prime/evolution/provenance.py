"""Tamper-evident manifests for evolution experiments."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping


@dataclass(frozen=True)
class EvolutionManifest:
    """Immutable description of one evolution attempt."""

    run_id: str
    repository: str
    base_revision: str
    candidate_revision: str | None
    target: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    parent_manifest_hash: str | None = None
    benchmark: Mapping[str, Any] = field(default_factory=dict)
    tests: Mapping[str, Any] = field(default_factory=dict)
    policy: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def canonical_payload(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class ProvenanceChain:
    """Builds a hash-linked sequence of evolution manifests."""

    def __init__(self) -> None:
        self._manifests: list[tuple[EvolutionManifest, str]] = []

    @property
    def head(self) -> str | None:
        return self._manifests[-1][1] if self._manifests else None

    def append(self, manifest: EvolutionManifest) -> str:
        if manifest.parent_manifest_hash != self.head:
            raise ValueError("manifest parent does not match provenance-chain head")
        digest = manifest.digest()
        self._manifests.append((manifest, digest))
        return digest

    def export(self) -> list[dict[str, Any]]:
        return [
            {"manifest": manifest.canonical_payload(), "digest": digest}
            for manifest, digest in self._manifests
        ]

    def verify(self) -> bool:
        previous: str | None = None
        for manifest, digest in self._manifests:
            if manifest.parent_manifest_hash != previous or manifest.digest() != digest:
                return False
            previous = digest
        return True
