"""Execution node model for the graph-native execution substrate."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from thalos_prime.execution_ir.hash import hash_dict


class NodeKind(Enum):
    """Classifies the role of a node within an execution graph."""

    SOURCE = "SOURCE"
    TRANSFORM = "TRANSFORM"
    SINK = "SINK"
    CONTROL = "CONTROL"
    ASSERT = "ASSERT"
    CHECKPOINT = "CHECKPOINT"
    EXTERNAL_CALL = "EXTERNAL_CALL"


class NodeStatus(Enum):
    """Tracks the execution status of a node."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    POISONED = "POISONED"


class FailureMode(Enum):
    """Controls how a node responds to execution failures."""

    FAIL_FAST = "FAIL_FAST"
    RETRY = "RETRY"
    SKIP = "SKIP"
    MARK_POISONED = "MARK_POISONED"


@dataclass
class ExecutionNode:
    """Represents a single node in the execution graph.

    Each node encapsulates an operation with its inputs, outputs,
    dependencies, and execution metadata. Hashes provide
    deterministic content addressing for replay and provenance.
    """

    id: str
    operation: str
    kind: NodeKind
    inputs: dict[str, object]
    outputs: dict[str, object]
    dependencies: list[str]
    input_hash: str
    output_hash: str
    environment_signature: str
    plugin_version: str
    rule_version: str
    status: NodeStatus
    failure_mode: FailureMode
    created_at: str
    started_at: str | None
    finished_at: str | None
    tags: list[str] = field(default_factory=list)
    error: str | None = None

    def compute_input_hash(self) -> str:
        """Compute and return a deterministic hash of the node's inputs.

        Returns:
            Hex SHA-256 digest of the stable-JSON-serialized inputs.

        """
        return hash_dict(self.inputs)

    def compute_output_hash(self) -> str:
        """Compute and return a deterministic hash of the node's outputs.

        Returns:
            Hex SHA-256 digest of the stable-JSON-serialized outputs.

        """
        return hash_dict(self.outputs)

    def to_dict(self) -> dict[str, object]:
        """Serialize this node to a JSON-safe dictionary.

        Returns:
            Dictionary containing all node fields with enum values as strings.

        """
        return {
            "id": self.id,
            "operation": self.operation,
            "kind": self.kind.value,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "dependencies": self.dependencies,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "environment_signature": self.environment_signature,
            "plugin_version": self.plugin_version,
            "rule_version": self.rule_version,
            "status": self.status.value,
            "failure_mode": self.failure_mode.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "tags": self.tags,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> ExecutionNode:
        """Deserialize a node from a dictionary produced by to_dict().

        Args:
            d: Dictionary in the format produced by to_dict().

        Returns:
            Reconstructed ExecutionNode instance.

        """
        raw_inputs = d["inputs"]
        raw_outputs = d["outputs"]
        raw_deps = d["dependencies"]
        raw_tags = d.get("tags")
        raw_inputs_typed: dict[str, object] = (
            {str(k): v for k, v in raw_inputs.items()}
            if isinstance(raw_inputs, dict)
            else {}
        )
        raw_outputs_typed: dict[str, object] = (
            {str(k): v for k, v in raw_outputs.items()}
            if isinstance(raw_outputs, dict)
            else {}
        )
        raw_deps_typed: list[str] = [str(x) for x in raw_deps] if isinstance(raw_deps, list) else []
        raw_tags_typed: list[str] = [str(x) for x in raw_tags] if isinstance(raw_tags, list) else []
        return cls(
            id=str(d["id"]),
            operation=str(d["operation"]),
            kind=NodeKind(str(d["kind"])),
            inputs=raw_inputs_typed,
            outputs=raw_outputs_typed,
            dependencies=raw_deps_typed,
            input_hash=str(d["input_hash"]),
            output_hash=str(d["output_hash"]),
            environment_signature=str(d["environment_signature"]),
            plugin_version=str(d["plugin_version"]),
            rule_version=str(d["rule_version"]),
            status=NodeStatus(str(d["status"])),
            failure_mode=FailureMode(str(d["failure_mode"])),
            created_at=str(d["created_at"]),
            started_at=str(d["started_at"]) if d.get("started_at") is not None else None,
            finished_at=str(d["finished_at"]) if d.get("finished_at") is not None else None,
            tags=raw_tags_typed,
            error=str(d["error"]) if d.get("error") is not None else None,
        )


__all__ = ["ExecutionNode", "FailureMode", "NodeKind", "NodeStatus"]
