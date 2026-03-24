"""Provenance index — records per-node execution provenance."""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from pathlib import Path

from thalos_prime.execution_ir.node import ExecutionNode
from thalos_prime.storage.provider import get_storage_base_path


@dataclass
class ProvenanceRecord:
    """Records the provenance of a single node execution.

    Captures input and output content hashes, the environment signature,
    and the operation name for audit and replay purposes.
    """

    graph_id: str
    node_id: str
    input_hash: str
    output_hash: str
    environment_signature: str
    operation: str
    recorded_at: str

    def to_dict(self) -> dict[str, object]:
        """Serialize this record to a JSON-safe dictionary.

        Returns:
            Dictionary representation of this provenance record.

        """
        return {
            "graph_id": self.graph_id,
            "node_id": self.node_id,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "environment_signature": self.environment_signature,
            "operation": self.operation,
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> ProvenanceRecord:
        """Deserialize a ProvenanceRecord from a dictionary.

        Args:
            d: Dictionary in the format produced by to_dict().

        Returns:
            Reconstructed ProvenanceRecord instance.

        """
        return cls(
            graph_id=str(d["graph_id"]),
            node_id=str(d["node_id"]),
            input_hash=str(d["input_hash"]),
            output_hash=str(d["output_hash"]),
            environment_signature=str(d["environment_signature"]),
            operation=str(d["operation"]),
            recorded_at=str(d["recorded_at"]),
        )


class ProvenanceIndex:
    """Stores and retrieves per-node execution provenance records.

    Records are stored as JSONL files under
    ``base_path/provenance/{graph_id}.jsonl``.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize the provenance index with an optional custom base path.

        Args:
            base_path: Root directory for provenance storage. Uses the default
                from get_storage_base_path() if not provided.

        """
        base = base_path if base_path is not None else get_storage_base_path()
        self._base = base / "provenance"
        self._base.mkdir(parents=True, exist_ok=True)

    def _record_path(self, graph_id: str) -> Path:
        """Return the JSONL path for a graph's provenance records.

        Args:
            graph_id: Unique graph identifier.

        Returns:
            Path to the graph's provenance file.

        """
        return self._base / f"{graph_id}.jsonl"

    def record_node(self, graph_id: str, node: ExecutionNode) -> ProvenanceRecord:
        """Record the provenance of a single node execution.

        Args:
            graph_id: ID of the graph containing this node.
            node: ExecutionNode whose provenance to record.

        Returns:
            The newly created ProvenanceRecord.

        """
        record = ProvenanceRecord(
            graph_id=graph_id,
            node_id=node.id,
            input_hash=node.input_hash,
            output_hash=node.output_hash,
            environment_signature=node.environment_signature,
            operation=node.operation,
            recorded_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )
        path = self._record_path(graph_id)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return record

    def get_by_node(self, graph_id: str, node_id: str) -> ProvenanceRecord | None:
        """Return the provenance record for a specific node, or None.

        If multiple records exist for the same node (e.g. after replay),
        returns the most recently recorded one.

        Args:
            graph_id: Unique graph identifier.
            node_id: Node ID to look up.

        Returns:
            Most recent ProvenanceRecord for this node, or None if not found.

        """
        records = [r for r in self.get_by_graph(graph_id) if r.node_id == node_id]
        return records[-1] if records else None

    def get_by_graph(self, graph_id: str) -> list[ProvenanceRecord]:
        """Return all provenance records for the given graph ID.

        Args:
            graph_id: Unique graph identifier.

        Returns:
            List of ProvenanceRecords in append order.

        """
        path = self._record_path(graph_id)
        if not path.exists():
            return []
        records: list[ProvenanceRecord] = []
        with path.open(encoding="utf-8") as fh:
            for raw_line in fh:
                stripped = raw_line.strip()
                if stripped:
                    data: dict[str, object] = json.loads(stripped)
                    records.append(ProvenanceRecord.from_dict(data))
        return records


__all__ = ["ProvenanceIndex", "ProvenanceRecord"]
