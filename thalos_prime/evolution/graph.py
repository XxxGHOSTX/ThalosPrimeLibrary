"""Mutable execution graphs for THALOS Prime workflows."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    function: str
    role: str = "worker"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphWorkflow:
    workflow_id: str
    nodes: dict[str, GraphNode]
    connections: list[tuple[str, str]]
    generation: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def clone(self, workflow_id: str | None = None) -> "GraphWorkflow":
        return GraphWorkflow(
            workflow_id=workflow_id or self.workflow_id,
            nodes=dict(self.nodes),
            connections=list(self.connections),
            generation=self.generation,
            metadata=dict(self.metadata),
        )

    def validate(self) -> None:
        ids = set(self.nodes)
        for left, right in self.connections:
            if left not in ids or right not in ids:
                raise ValueError(f"graph edge references unknown node: {left}->{right}")
        self._assert_acyclic()

    def _assert_acyclic(self) -> None:
        adjacency: dict[str, list[str]] = {key: [] for key in self.nodes}
        for left, right in self.connections:
            adjacency[left].append(right)
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("execution graph contains a cycle")
            if node in visited:
                return
            visiting.add(node)
            for child in adjacency[node]:
                visit(child)
            visiting.remove(node)
            visited.add(node)

        for node in self.nodes:
            visit(node)

    def topological_order(self) -> list[str]:
        self.validate()
        incoming = {key: 0 for key in self.nodes}
        adjacency: dict[str, list[str]] = {key: [] for key in self.nodes}
        for left, right in self.connections:
            adjacency[left].append(right)
            incoming[right] += 1
        queue = sorted(key for key, count in incoming.items() if count == 0)
        order: list[str] = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for child in sorted(adjacency[node]):
                incoming[child] -= 1
                if incoming[child] == 0:
                    queue.append(child)
                    queue.sort()
        if len(order) != len(self.nodes):
            raise ValueError("graph could not be topologically ordered")
        return order

    def replace_function(self, node_id: str, function: str) -> "GraphWorkflow":
        if node_id not in self.nodes:
            raise KeyError(node_id)
        candidate = self.clone()
        old = candidate.nodes[node_id]
        candidate.nodes[node_id] = GraphNode(
            node_id=old.node_id, function=function, role=old.role, metadata=dict(old.metadata)
        )
        candidate.generation += 1
        candidate.validate()
        return candidate


class ExecutionGraph:
    """Registry of named versioned workflows."""

    def __init__(self) -> None:
        self._workflows: dict[str, GraphWorkflow] = {}
        self._active: dict[str, str] = {}

    def register(self, workflow: GraphWorkflow, active: bool = False) -> None:
        workflow.validate()
        self._workflows[workflow.workflow_id] = workflow
        if active or workflow.workflow_id not in self._active:
            self._active[workflow.workflow_id] = workflow.workflow_id

    def get(self, workflow_id: str) -> GraphWorkflow:
        return self._workflows[workflow_id]

    def active(self, workflow_family: str) -> GraphWorkflow:
        return self._workflows[self._active[workflow_family]]

    def promote(self, workflow_family: str, workflow_id: str) -> None:
        if workflow_id not in self._workflows:
            raise KeyError(workflow_id)
        self._active[workflow_family] = workflow_id

    def snapshot(self) -> dict[str, Any]:
        return {
            "workflows": sorted(self._workflows),
            "active": dict(sorted(self._active.items())),
        }
