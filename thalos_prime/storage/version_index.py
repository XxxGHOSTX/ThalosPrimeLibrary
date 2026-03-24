"""Version index for tracking graph version history and parent-child relationships."""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from pathlib import Path

from thalos_prime.execution_ir.graph import ExecutionGraph
from thalos_prime.storage.provider import get_storage_base_path


@dataclass
class VersionRecord:
    """Records a single version of a graph in the version index.

    Tracks the graph ID, version number, parent lineage, content hash,
    and creation timestamp.
    """

    graph_id: str
    version: int
    parent_id: str | None
    graph_hash: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        """Serialize this record to a JSON-safe dictionary.

        Returns:
            Dictionary representation of this version record.

        """
        return {
            "graph_id": self.graph_id,
            "version": self.version,
            "parent_id": self.parent_id,
            "graph_hash": self.graph_hash,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> VersionRecord:
        """Deserialize a VersionRecord from a dictionary.

        Args:
            d: Dictionary in the format produced by to_dict().

        Returns:
            Reconstructed VersionRecord instance.

        """
        return cls(
            graph_id=str(d["graph_id"]),
            version=int(str(d["version"])),
            parent_id=str(d["parent_id"]) if d.get("parent_id") is not None else None,
            graph_hash=str(d["graph_hash"]),
            created_at=str(d["created_at"]),
        )


class VersionIndex:
    """Tracks graph versions and parent-child relationships.

    Each graph's version history is stored as a JSONL file under
    ``base_path/versions/{graph_id}.jsonl``.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize the version index with an optional custom base path.

        Args:
            base_path: Root directory for version index storage. Uses the default
                from get_storage_base_path() if not provided.

        """
        self._base = (base_path if base_path is not None else get_storage_base_path()) / "versions"
        self._base.mkdir(parents=True, exist_ok=True)

    def _index_path(self, graph_id: str) -> Path:
        """Return the JSONL file path for a specific graph's version index.

        Args:
            graph_id: Unique graph identifier.

        Returns:
            Path to the graph's version index file.

        """
        return self._base / f"{graph_id}.jsonl"

    def record(self, graph: ExecutionGraph) -> None:
        """Record the current version of a graph in the index.

        Args:
            graph: ExecutionGraph whose version to record.

        """
        record = VersionRecord(
            graph_id=graph.id,
            version=graph.version,
            parent_id=graph.parent_id,
            graph_hash=graph.graph_hash,
            created_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )
        path = self._index_path(graph.id)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def get_versions(self, graph_id: str) -> list[VersionRecord]:
        """Return all version records for the given graph ID.

        Args:
            graph_id: Unique graph identifier.

        Returns:
            List of VersionRecord entries in append order.

        """
        path = self._index_path(graph_id)
        if not path.exists():
            return []
        records: list[VersionRecord] = []
        with path.open(encoding="utf-8") as fh:
            for raw_line in fh:
                stripped = raw_line.strip()
                if stripped:
                    data: dict[str, object] = json.loads(stripped)
                    records.append(VersionRecord.from_dict(data))
        return records

    def get_children(self, parent_id: str) -> list[str]:
        """Return graph IDs that list the given graph as their parent.

        Scans all index files for parent_id references. Returns unique
        child graph IDs in sorted order.

        Args:
            parent_id: Graph ID to search for as a parent.

        Returns:
            Sorted list of child graph IDs.

        """
        children: set[str] = set()
        if not self._base.exists():
            return []
        for path in self._base.glob("*.jsonl"):
            with path.open(encoding="utf-8") as fh:
                for raw_line in fh:
                    stripped = raw_line.strip()
                    if not stripped:
                        continue
                    data: dict[str, object] = json.loads(stripped)
                    if data.get("parent_id") == parent_id:
                        children.add(str(data["graph_id"]))
        return sorted(children)


__all__ = ["VersionIndex", "VersionRecord"]
