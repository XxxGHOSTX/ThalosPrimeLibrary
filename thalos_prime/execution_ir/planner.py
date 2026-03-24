"""Topological planner for execution graphs using Kahn's algorithm."""

from __future__ import annotations

import collections

from thalos_prime.execution_ir.graph import ExecutionGraph


class ExecutionPlanner:
    """Plans node execution order for an ExecutionGraph.

    Uses Kahn's algorithm to produce a topologically sorted list of node IDs.
    The graph must be a valid DAG; cycles raise ValueError.
    """

    def plan(self, graph: ExecutionGraph) -> list[str]:
        """Return topologically sorted node IDs for the given graph.

        Validates the DAG first, then performs Kahn's topological sort.

        Args:
            graph: ExecutionGraph to plan. Must be acyclic.

        Returns:
            List of node IDs in a valid execution order (sources first).

        Raises:
            ValueError: If the graph contains a cycle.

        """
        graph.validate_dag()

        # Build adjacency list and in-degree map
        in_degree: dict[str, int] = {nid: 0 for nid in graph.nodes}
        adjacency: dict[str, list[str]] = {nid: [] for nid in graph.nodes}

        for src, dst in graph.edges:
            if src in adjacency and dst in in_degree:
                adjacency[src].append(dst)
                in_degree[dst] += 1

        # Kahn's algorithm — use deque for O(1) popleft; sort for determinism
        queue: collections.deque[str] = collections.deque(
            sorted(nid for nid, deg in in_degree.items() if deg == 0)
        )
        order: list[str] = []

        while queue:
            node_id = queue.popleft()
            order.append(node_id)
            newly_free: list[str] = []
            for neighbour in adjacency.get(node_id, []):
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    newly_free.append(neighbour)
            for nid in sorted(newly_free):
                queue.append(nid)

        if len(order) != len(graph.nodes):
            msg = f"Cycle detected during planning of graph '{graph.id}'"
            raise ValueError(msg)

        return order


__all__ = ["ExecutionPlanner"]
