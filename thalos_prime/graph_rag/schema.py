"""Schema definitions for the GraphRAG knowledge graph.

Defines all node types, edge types, and schema version constants used by the
thalos_prime.graph_rag module.  All dataclasses are frozen (immutable) to
enforce deterministic state.

Control Plane: GraphRAGControlPlane (control_plane.py)
Data Plane: GraphIngestionPipeline (ingestion.py), GraphRetriever (retrieval.py)
"""

from __future__ import annotations

from dataclasses import dataclass, field

GRAPH_SCHEMA_VERSION: str = "1.0"

# Seed XOR salt for GraphRAG — "GRAG" in ASCII hex
GRAPH_RAG_SEED_SALT: int = 0x47524147


# ---------------------------------------------------------------------------
# Node dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EntityNode:
    """A named entity extracted from a CanonicalArtifact.

    id is the stable SHA-256 of (entity_type + ":" + canonical_name).
    """

    id: str
    entity_type: str
    canonical_name: str
    aliases: list[str]
    provenance: list[str]
    created_at: float
    version: str = GRAPH_SCHEMA_VERSION


@dataclass
class FragmentNode:
    """A text fragment from a CanonicalArtifact stored as a graph node."""

    id: str
    artifact_id: str
    char_offset: int
    text: str
    meaning_hash: str
    coherence_score: float
    version: str = GRAPH_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Edge dataclasses
# ---------------------------------------------------------------------------


@dataclass
class RelationshipEdge:
    """A directed relationship between two EntityNodes."""

    source_id: str
    target_id: str
    relation_type: str
    weight: float
    provenance: list[str]
    version: str = GRAPH_SCHEMA_VERSION


@dataclass
class ContainsEdge:
    """An edge from a FragmentNode to an EntityNode (entity mention)."""

    fragment_id: str
    entity_id: str
    span_start: int
    span_end: int
    version: str = GRAPH_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Retrieval result
# ---------------------------------------------------------------------------


@dataclass
class GraphRetrievalResult:
    """A single result from a GraphRetriever query."""

    fragment_id: str
    artifact_id: str
    text: str
    graph_score: float
    text_score: float
    final_score: float
    hop_distance: int
    entity_ids: list[str] = field(default_factory=list)
    version: str = GRAPH_SCHEMA_VERSION
