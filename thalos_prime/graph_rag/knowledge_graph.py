"""Knowledge graph wrapper for the GraphRAG module.

KnowledgeGraph provides a typed API over a networkx.DiGraph, managing
EntityNode, FragmentNode, RelationshipEdge, and ContainsEdge objects.
All mutation operations log deterministic state transitions.

Control Plane: GraphRAGControlPlane
Data Plane: this module (pure data structure, no lifecycle logic)
"""

from __future__ import annotations

import json
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

import networkx as nx

from thalos_prime.graph_rag.schema import (
    GRAPH_SCHEMA_VERSION,
    ContainsEdge,
    EntityNode,
    FragmentNode,
    RelationshipEdge,
)

# Node type sentinel stored as a node attribute
_NODE_TYPE_ENTITY = "entity"
_NODE_TYPE_FRAGMENT = "fragment"


class KnowledgeGraph:
    """Typed wrapper over networkx.DiGraph for the Thalos Prime GraphRAG module.

    All node and edge insertions are deterministic: IDs are SHA-256 derived
    and insertion order follows char-offset order from the ingestion pipeline.

    State surfaces:
        _graph: the underlying networkx.DiGraph
        node_count: observable count of all nodes
        edge_count: observable count of all edges
    """

    def __init__(self) -> None:
        """Initialize an empty knowledge graph."""
        self._graph: nx.DiGraph = nx.DiGraph()

    # ------------------------------------------------------------------
    # Observable state
    # ------------------------------------------------------------------

    @property
    def node_count(self) -> int:
        """Return total number of nodes."""
        return int(self._graph.number_of_nodes())

    @property
    def edge_count(self) -> int:
        """Return total number of edges."""
        return int(self._graph.number_of_edges())

    # ------------------------------------------------------------------
    # Entity nodes
    # ------------------------------------------------------------------

    def upsert_entity(self, node: EntityNode) -> bool:
        """Insert or update an EntityNode.

        Returns True if the node was newly created, False if updated.
        """
        is_new = node.id not in self._graph
        self._graph.add_node(
            node.id,
            node_type=_NODE_TYPE_ENTITY,
            entity_type=node.entity_type,
            canonical_name=node.canonical_name,
            aliases=list(node.aliases),
            provenance=list(node.provenance),
            created_at=node.created_at,
            version=node.version,
        )
        return is_new

    def get_entity(self, node_id: str) -> EntityNode | None:
        """Return an EntityNode by id, or None if absent."""
        if node_id not in self._graph:
            return None
        attrs = self._graph.nodes[node_id]
        if attrs.get("node_type") != _NODE_TYPE_ENTITY:
            return None
        return EntityNode(
            id=node_id,
            entity_type=str(attrs["entity_type"]),
            canonical_name=str(attrs["canonical_name"]),
            aliases=list(attrs["aliases"]),
            provenance=list(attrs["provenance"]),
            created_at=float(attrs["created_at"]),
            version=str(attrs.get("version", GRAPH_SCHEMA_VERSION)),
        )

    def find_entity_by_name(self, canonical_name: str) -> EntityNode | None:
        """Return the first EntityNode whose canonical_name matches exactly."""
        for nid, attrs in self._graph.nodes(data=True):
            if (
                attrs.get("node_type") == _NODE_TYPE_ENTITY
                and attrs.get("canonical_name") == canonical_name
            ):
                return self.get_entity(str(nid))
        return None

    def find_entity_by_alias(self, alias: str) -> list[EntityNode]:
        """Return all EntityNodes whose aliases list contains alias."""
        results: list[EntityNode] = []
        for nid, attrs in self._graph.nodes(data=True):
            if attrs.get("node_type") != _NODE_TYPE_ENTITY:
                continue
            if alias in attrs.get("aliases", []):
                node = self.get_entity(str(nid))
                if node is not None:
                    results.append(node)
        return sorted(results, key=lambda n: n.id)

    # ------------------------------------------------------------------
    # Fragment nodes
    # ------------------------------------------------------------------

    def upsert_fragment(self, node: FragmentNode) -> bool:
        """Insert or update a FragmentNode.

        Returns True if the node was newly created, False if updated.
        """
        is_new = node.id not in self._graph
        self._graph.add_node(
            node.id,
            node_type=_NODE_TYPE_FRAGMENT,
            artifact_id=node.artifact_id,
            char_offset=node.char_offset,
            text=node.text,
            meaning_hash=node.meaning_hash,
            coherence_score=node.coherence_score,
            version=node.version,
        )
        return is_new

    def get_fragment(self, node_id: str) -> FragmentNode | None:
        """Return a FragmentNode by id, or None if absent."""
        if node_id not in self._graph:
            return None
        attrs = self._graph.nodes[node_id]
        if attrs.get("node_type") != _NODE_TYPE_FRAGMENT:
            return None
        return FragmentNode(
            id=node_id,
            artifact_id=str(attrs["artifact_id"]),
            char_offset=int(attrs["char_offset"]),
            text=str(attrs["text"]),
            meaning_hash=str(attrs["meaning_hash"]),
            coherence_score=float(attrs["coherence_score"]),
            version=str(attrs.get("version", GRAPH_SCHEMA_VERSION)),
        )

    def fragments_for_entity(self, entity_id: str) -> list[FragmentNode]:
        """Return all FragmentNodes connected to entity_id via ContainsEdge."""
        results: list[FragmentNode] = []
        for pred in self._graph.predecessors(entity_id):
            attrs = self._graph.nodes[pred]
            if attrs.get("node_type") == _NODE_TYPE_FRAGMENT:
                frag = self.get_fragment(str(pred))
                if frag is not None:
                    results.append(frag)
        return sorted(results, key=lambda f: (f.char_offset, f.id))

    def orphaned_fragment_ids(self) -> list[str]:
        """Return IDs of FragmentNodes that have no ContainsEdge (no entity link)."""
        orphans: list[str] = []
        for nid, attrs in self._graph.nodes(data=True):
            if attrs.get("node_type") != _NODE_TYPE_FRAGMENT:
                continue
            if self._graph.out_degree(nid) == 0:
                orphans.append(str(nid))
        return sorted(orphans)

    # ------------------------------------------------------------------
    # Edges
    # ------------------------------------------------------------------

    def add_relationship(self, edge: RelationshipEdge) -> None:
        """Add or update a RelationshipEdge between two EntityNodes."""
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            relation_type=edge.relation_type,
            weight=edge.weight,
            provenance=list(edge.provenance),
            version=edge.version,
        )

    def add_contains(self, edge: ContainsEdge) -> None:
        """Add a ContainsEdge from a FragmentNode to an EntityNode."""
        self._graph.add_edge(
            edge.fragment_id,
            edge.entity_id,
            relation_type="contains",
            span_start=edge.span_start,
            span_end=edge.span_end,
            weight=1.0,
            version=edge.version,
        )

    def neighbors_of(self, node_id: str) -> list[tuple[str, dict[str, Any]]]:
        """Return sorted (neighbor_id, edge_attrs) list for node_id successors."""
        result = [
            (str(nbr), dict(self._graph[node_id][nbr]))
            for nbr in self._graph.successors(node_id)
        ]
        # Deterministic order: weight DESC, node_id ASC
        return sorted(result, key=lambda t: (-t[1].get("weight", 0.0), t[0]))

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _entity_node_id(entity_type: str, canonical_name: str) -> str:
        """Compute stable SHA-256 id for an entity."""
        raw = f"{entity_type}:{canonical_name}"
        return sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph to a JSON-compatible dictionary."""
        return {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "nodes": [
                {"id": str(nid), **dict(attrs)}
                for nid, attrs in self._graph.nodes(data=True)
            ],
            "edges": [
                {"source": str(u), "target": str(v), **dict(d)}
                for u, v, d in self._graph.edges(data=True)
            ],
        }

    def snapshot(self, path: Path) -> None:
        """Write an atomic JSONL snapshot of the graph to path.

        Uses tmp-file + rename for atomicity on POSIX systems.
        """
        data = self.to_dict()
        data["timestamp"] = time.time()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeGraph:
        """Reconstruct a KnowledgeGraph from a serialized dictionary."""
        kg = cls()
        for node_raw in data.get("nodes", []):
            nid = str(node_raw["id"])
            attrs = {k: v for k, v in node_raw.items() if k != "id"}
            kg._graph.add_node(nid, **attrs)
        for edge_raw in data.get("edges", []):
            src = str(edge_raw["source"])
            tgt = str(edge_raw["target"])
            attrs = {k: v for k, v in edge_raw.items() if k not in ("source", "target")}
            kg._graph.add_edge(src, tgt, **attrs)
        return kg
