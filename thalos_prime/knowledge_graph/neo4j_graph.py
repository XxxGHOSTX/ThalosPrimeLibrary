"""Thalos Prime - Neo4j Knowledge Graph Layer.

Control Plane component providing a Neo4j-compatible knowledge graph interface
backed by NetworkX for local deterministic operation. Supports Cypher-style
query building, node/relationship CRUD, pattern matching, and path traversal.

Control Plane boundary: coordinates graph state and lifecycle only.
Query execution is data-plane work dispatched through the graph backend.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal, TypedDict

import networkx as nx

from thalos_prime.library_of_sense.core.interfaces import ValidationResult
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)

# Safe label/type pattern: alphanumeric + underscores only
_LABEL_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class NodeRecordDict(TypedDict):
    """Serialized representation of a node record."""

    node_id: str
    labels: list[str]
    properties: dict[str, object]


class RelationshipRecordDict(TypedDict):
    """Serialized representation of a relationship record."""

    source_id: str
    target_id: str
    rel_type: str
    properties: dict[str, object]


class CypherQueryDict(TypedDict):
    """Serialized representation of a Cypher query."""

    operation: Literal["match_nodes", "match_relationships", "shortest_path", "neighbors"]
    node_label: str
    rel_type: str
    source_id: str
    target_id: str
    properties: dict[str, object]
    limit: int


@dataclass
class NodeRecord:
    """A labeled node with typed properties in the knowledge graph.

    Attributes:
        node_id: Unique deterministic identifier for this node.
        labels: Set of classification labels (e.g., "Person", "Concept").
        properties: Key-value property map for this node.

    """

    node_id: str
    labels: set[str] = field(default_factory=set)
    properties: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> NodeRecordDict:
        """Serialize node to dictionary.

        Returns:
            Dictionary representation of this node.

        """
        return {
            "node_id": self.node_id,
            "labels": sorted(self.labels),
            "properties": dict(self.properties),
        }


@dataclass
class RelationshipRecord:
    """A typed directed relationship between two nodes.

    Attributes:
        source_id: Source node identifier.
        target_id: Target node identifier.
        rel_type: Relationship type label (e.g., "KNOWS", "DEPENDS_ON").
        properties: Key-value property map for this relationship.

    """

    source_id: str
    target_id: str
    rel_type: str
    properties: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> RelationshipRecordDict:
        """Serialize relationship to dictionary.

        Returns:
            Dictionary representation of this relationship.

        """
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "rel_type": self.rel_type,
            "properties": dict(self.properties),
        }


@dataclass
class CypherQuery:
    """A structured Cypher-style query specification.

    Attributes:
        operation: The query operation type.
        node_label: Optional label filter for node queries.
        rel_type: Optional relationship type filter.
        source_id: Optional source node for relationship queries.
        target_id: Optional target node for relationship queries.
        properties: Property filters to match against.
        limit: Maximum number of results to return.

    """

    operation: Literal["match_nodes", "match_relationships", "shortest_path", "neighbors"]
    node_label: str = ""
    rel_type: str = ""
    source_id: str = ""
    target_id: str = ""
    properties: dict[str, object] = field(default_factory=dict)
    limit: int = 100

    def to_dict(self) -> CypherQueryDict:
        """Serialize query to dictionary.

        Returns:
            Dictionary representation of this query.

        """
        return {
            "operation": self.operation,
            "node_label": self.node_label,
            "rel_type": self.rel_type,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "properties": dict(self.properties),
            "limit": self.limit,
        }


def _validate_label(label: str) -> None:
    """Validate that a label or type string is safe.

    Args:
        label: The label or relationship type to validate.

    Raises:
        ValueError: If the label contains unsafe characters.

    """
    if not _LABEL_PATTERN.match(label):
        msg = f"Invalid label or type: {label!r}. Must match [A-Za-z_][A-Za-z0-9_]*"
        raise ValueError(msg)


class Neo4jKnowledgeGraph(BaseLifecycleComponent):
    """Neo4j-compatible knowledge graph with deterministic local backend.

    Provides node and relationship CRUD, Cypher-style query execution,
    pattern matching, and shortest-path traversal. Backed by NetworkX
    DiGraph for local deterministic operation without requiring a Neo4j server.

    All operations are deterministic: identical sequences of mutations
    produce identical graph state.
    """

    def __init__(self, seed: int = 0) -> None:
        """Initialize the Neo4j knowledge graph layer.

        Args:
            seed: Deterministic seed for replay identification.

        """
        super().__init__("Neo4jKnowledgeGraph", seed=seed)
        self._graph: nx.DiGraph = nx.DiGraph()
        self._node_count: int = 0
        self._rel_count: int = 0
        self._query_count: int = 0

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Create the internal graph and mark as initialized."""
        self._graph = nx.DiGraph()
        self._node_count = 0
        self._rel_count = 0
        self._query_count = 0
        self._initialized = True
        self._emit_event("initialize", "graph created, counters reset")
        logger.debug("Neo4jKnowledgeGraph initialized")

    def validate(self) -> ValidationResult:
        """Validate the knowledge graph is ready for operations.

        Returns:
            ValidationResult indicating readiness.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="Neo4jKnowledgeGraph not initialized; call initialize() first",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"Neo4jKnowledgeGraph ready: nodes={self._node_count} "
                f"relationships={self._rel_count}"
            ),
        )

    def operate(self) -> None:
        """Log current graph statistics. Idempotent."""
        self._emit_event(
            "operate",
            f"nodes={self._node_count} rels={self._rel_count} queries={self._query_count}",
        )

    def reconcile(self) -> None:
        """Verify graph consistency and fix counter drift.

        Raises:
            TypeError: If a relationship type attribute is not a string.

        """
        self._emit_event("reconcile", "verifying graph consistency")
        for u, v, data in self._graph.edges(data=True):
            rel_type = data.get("rel_type", "")
            if not isinstance(rel_type, str):
                msg = (
                    f"Corrupt rel_type on edge ({u!r} -> {v!r}): "
                    f"expected str, got {type(rel_type).__name__!r}"
                )
                raise TypeError(msg)
        # Reconcile counts to actual graph state
        self._node_count = self._graph.number_of_nodes()
        self._rel_count = self._graph.number_of_edges()
        self._emit_event("reconcile", "graph consistency verified")

    def checkpoint(self) -> dict[str, object]:
        """Serialize full graph state for restart.

        Returns:
            Dictionary with all nodes, relationships, and counters.

        """
        nodes: list[dict[str, object]] = []
        for node_id, data in self._graph.nodes(data=True):
            nodes.append({
                "node_id": str(node_id),
                "labels": sorted(data.get("labels", set())),
                "properties": dict(data.get("properties", {})),
            })
        relationships: list[dict[str, object]] = []
        for u, v, data in self._graph.edges(data=True):
            relationships.append({
                "source_id": str(u),
                "target_id": str(v),
                "rel_type": str(data.get("rel_type", "")),
                "properties": dict(data.get("properties", {})),
            })
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "node_count": self._node_count,
            "rel_count": self._rel_count,
            "query_count": self._query_count,
            "nodes": nodes,
            "relationships": relationships,
        }
        self._emit_event("checkpoint", f"nodes={self._node_count} rels={self._rel_count}")
        return state

    def terminate(self) -> None:
        """Clear all graph data and mark as uninitialized."""
        self._graph.clear()
        self._node_count = 0
        self._rel_count = 0
        self._query_count = 0
        self._initialized = False
        self._emit_event("terminate", "graph cleared")
        logger.debug("Neo4jKnowledgeGraph terminated")

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    def create_node(self, record: NodeRecord) -> NodeRecord:
        """Create or update a labeled node in the graph.

        Args:
            record: NodeRecord with node_id, labels, and properties.

        Returns:
            The created/updated NodeRecord.

        Raises:
            ValueError: If any label is invalid.

        """
        for label in record.labels:
            _validate_label(label)
        is_new = record.node_id not in self._graph
        self._graph.add_node(
            record.node_id,
            labels=set(record.labels),
            properties=dict(record.properties),
        )
        if is_new:
            self._node_count += 1
        logger.debug("Created node: %s labels=%s", record.node_id, record.labels)
        return record

    def get_node(self, node_id: str) -> NodeRecord | None:
        """Retrieve a node by its identifier.

        Args:
            node_id: The node identifier to look up.

        Returns:
            NodeRecord if found, None otherwise.

        """
        if node_id not in self._graph:
            return None
        data = self._graph.nodes[node_id]
        return NodeRecord(
            node_id=node_id,
            labels=set(data.get("labels", set())),
            properties=dict(data.get("properties", {})),
        )

    def delete_node(self, node_id: str) -> bool:
        """Remove a node and all its incident relationships.

        Args:
            node_id: The node identifier to remove.

        Returns:
            True if the node existed and was removed, False otherwise.

        """
        if node_id not in self._graph:
            return False
        incident_edges = self._graph.in_degree(node_id) + self._graph.out_degree(node_id)
        self._graph.remove_node(node_id)
        self._node_count -= 1
        self._rel_count -= incident_edges
        logger.debug("Deleted node: %s (removed %d edges)", node_id, incident_edges)
        return True

    # ------------------------------------------------------------------
    # Relationship CRUD
    # ------------------------------------------------------------------

    def create_relationship(self, record: RelationshipRecord) -> RelationshipRecord:
        """Create a typed directed relationship between two nodes.

        Creates source/target nodes if they do not exist.

        Args:
            record: RelationshipRecord defining the relationship.

        Returns:
            The created RelationshipRecord.

        Raises:
            ValueError: If the relationship type is invalid.

        """
        _validate_label(record.rel_type)
        if record.source_id not in self._graph:
            self._graph.add_node(record.source_id, labels=set(), properties={})
            self._node_count += 1
        if record.target_id not in self._graph:
            self._graph.add_node(record.target_id, labels=set(), properties={})
            self._node_count += 1
        is_new = not self._graph.has_edge(record.source_id, record.target_id)
        self._graph.add_edge(
            record.source_id,
            record.target_id,
            rel_type=record.rel_type,
            properties=dict(record.properties),
        )
        if is_new:
            self._rel_count += 1
        logger.debug(
            "Created relationship: %s -[%s]-> %s",
            record.source_id,
            record.rel_type,
            record.target_id,
        )
        return record

    def get_relationships(
        self,
        source_id: str,
        rel_type: str = "",
    ) -> list[RelationshipRecord]:
        """Get all outgoing relationships from a node, optionally filtered by type.

        Args:
            source_id: Source node identifier.
            rel_type: Optional relationship type filter.

        Returns:
            List of matching RelationshipRecord instances.

        """
        if source_id not in self._graph:
            return []
        results: list[RelationshipRecord] = []
        for _, target, data in self._graph.out_edges(source_id, data=True):
            edge_type = str(data.get("rel_type", ""))
            if rel_type and edge_type != rel_type:
                continue
            results.append(
                RelationshipRecord(
                    source_id=source_id,
                    target_id=str(target),
                    rel_type=edge_type,
                    properties=dict(data.get("properties", {})),
                ),
            )
        return results

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    def execute_query(self, query: CypherQuery) -> list[dict[str, object]]:
        """Execute a Cypher-style query against the graph.

        Args:
            query: CypherQuery specifying the operation and filters.

        Returns:
            List of result dictionaries.

        Raises:
            ValueError: If the query operation is unknown.

        """
        self._query_count += 1
        if query.operation == "match_nodes":
            return self._match_nodes(query)
        if query.operation == "match_relationships":
            return self._match_relationships(query)
        if query.operation == "shortest_path":
            return self._shortest_path(query)
        if query.operation == "neighbors":
            return self._neighbors(query)
        msg = f"Unknown query operation: {query.operation!r}"
        raise ValueError(msg)

    def _match_nodes(self, query: CypherQuery) -> list[dict[str, object]]:
        """Match nodes by label and property filters.

        Args:
            query: CypherQuery with node_label and properties filters.

        Returns:
            List of matching node dictionaries.

        """
        results: list[dict[str, object]] = []
        for node_id, data in self._graph.nodes(data=True):
            labels: set[str] = data.get("labels", set())
            props: dict[str, object] = data.get("properties", {})
            if query.node_label and query.node_label not in labels:
                continue
            if not all(props.get(k) == v for k, v in query.properties.items()):
                continue
            results.append({
                "node_id": str(node_id),
                "labels": sorted(labels),
                "properties": dict(props),
            })
            if len(results) >= query.limit:
                break
        return results

    def _match_relationships(self, query: CypherQuery) -> list[dict[str, object]]:
        """Match relationships by type and source/target filters.

        Args:
            query: CypherQuery with rel_type, source_id, target_id filters.

        Returns:
            List of matching relationship dictionaries.

        """
        results: list[dict[str, object]] = []
        for u, v, data in self._graph.edges(data=True):
            edge_type = str(data.get("rel_type", ""))
            if query.rel_type and edge_type != query.rel_type:
                continue
            if query.source_id and str(u) != query.source_id:
                continue
            if query.target_id and str(v) != query.target_id:
                continue
            results.append({
                "source_id": str(u),
                "target_id": str(v),
                "rel_type": edge_type,
                "properties": dict(data.get("properties", {})),
            })
            if len(results) >= query.limit:
                break
        return results

    def _shortest_path(self, query: CypherQuery) -> list[dict[str, object]]:
        """Find shortest path between source and target nodes.

        Args:
            query: CypherQuery with source_id and target_id.

        Returns:
            List containing a single dict with the path, or empty list if no path.

        """
        if not query.source_id or not query.target_id:
            return []
        try:
            path: list[str] = [
                str(n) for n in nx.shortest_path(
                    self._graph, query.source_id, query.target_id,
                )
            ]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
        return [{"path": path, "length": len(path) - 1}]

    def _neighbors(self, query: CypherQuery) -> list[dict[str, object]]:
        """Get all neighbor nodes of a given source node.

        Args:
            query: CypherQuery with source_id.

        Returns:
            List of neighbor node dictionaries.

        """
        if not query.source_id or query.source_id not in self._graph:
            return []
        results: list[dict[str, object]] = []
        for neighbor in self._graph.successors(query.source_id):
            data = self._graph.nodes[neighbor]
            results.append({
                "node_id": str(neighbor),
                "labels": sorted(data.get("labels", set())),
                "properties": dict(data.get("properties", {})),
            })
            if len(results) >= query.limit:
                break
        return results

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return self._node_count

    @property
    def relationship_count(self) -> int:
        """Number of relationships in the graph."""
        return self._rel_count

    @property
    def query_count(self) -> int:
        """Number of queries executed against this graph."""
        return self._query_count


__all__ = [
    "CypherQuery",
    "Neo4jKnowledgeGraph",
    "NodeRecord",
    "RelationshipRecord",
]
