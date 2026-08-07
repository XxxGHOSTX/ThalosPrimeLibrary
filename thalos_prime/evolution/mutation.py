"""Mutation proposal generation for workflows and agent genomes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from .graph import GraphWorkflow


@dataclass(frozen=True)
class MutationProposal:
    mutation_id: str
    target: str
    old_version: str
    new_version: str
    change_type: str
    description: str
    confidence: float
    payload: dict[str, Any] = field(default_factory=dict)


class MutationEngine:
    """Produces explicit, replayable mutations rather than editing arbitrary files."""

    def propose_module(self, target: str, old_version: str, new_version: str, description: str, confidence: float, payload: dict[str, Any] | None = None) -> MutationProposal:
        return MutationProposal(
            mutation_id=str(uuid.uuid4()), target=target, old_version=old_version,
            new_version=new_version, change_type="module", description=description,
            confidence=max(0.0, min(1.0, confidence)), payload=dict(payload or {}),
        )

    def replace_graph_node(self, workflow: GraphWorkflow, node_id: str, new_function: str, new_version: str, description: str) -> tuple[GraphWorkflow, MutationProposal]:
        old = workflow.nodes[node_id].function
        candidate = workflow.replace_function(node_id, new_function)
        proposal = MutationProposal(
            mutation_id=str(uuid.uuid4()), target=f"{workflow.workflow_id}:{node_id}",
            old_version=old, new_version=new_version, change_type="workflow_node",
            description=description, confidence=1.0,
            payload={"node_id": node_id, "function": new_function},
        )
        return candidate, proposal
