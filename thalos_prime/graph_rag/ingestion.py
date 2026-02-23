"""GraphRAG ingestion pipeline (Data Plane).

Accepts CanonicalArtifact objects and populates a KnowledgeGraph with
EntityNode, FragmentNode, RelationshipEdge, and ContainsEdge objects.

All operations are deterministic: entity extraction is regex+vocabulary
driven, node IDs are SHA-256 derived, insertion order follows char offset.

Data Plane component — no lifecycle or coordination logic.
"""

from __future__ import annotations

import re
import time
from hashlib import sha256
from typing import NamedTuple

from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph
from thalos_prime.graph_rag.schema import (
    GRAPH_SCHEMA_VERSION,
    ContainsEdge,
    EntityNode,
    FragmentNode,
    RelationshipEdge,
)
from thalos_prime.ingest import CanonicalArtifact
from thalos_prime.lob_decoder import BabelDecoder

# Co-occurrence window (characters) for relationship extraction
_CO_OCCURRENCE_WINDOW: int = 256

# Very lightweight vocabulary-guided NER patterns:
# Each tuple: (compiled_regex, entity_type)
_NER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b"), "person"),
    (re.compile(r"\b([A-Z][a-z]{2,}(?:\s[A-Z][a-z]{2,})*)\b"), "concept"),
    (re.compile(r"\b(\d{4})\b"), "year"),
    (re.compile(r"\b([a-z]{4,}(?:tion|ment|ness|ity|ism|ology|graphy))\b"), "concept"),
]

_decoder = BabelDecoder()


class _ExtractedEntity(NamedTuple):
    span_start: int
    span_end: int
    text: str
    entity_type: str
    canonical_name: str


def _compute_entity_id(entity_type: str, canonical_name: str) -> str:
    """Stable SHA-256 id for an entity."""
    return sha256(f"{entity_type}:{canonical_name}".encode()).hexdigest()


def _compute_fragment_id(artifact_id: str, char_offset: int) -> str:
    """Stable SHA-256 id for a fragment."""
    return sha256(f"{artifact_id}:{char_offset}".encode()).hexdigest()


def _extract_entities(text: str) -> list[_ExtractedEntity]:
    """Extract named entities from text using deterministic regex patterns.

    Entities are sorted by (span_start, entity_type) for stable ordering.
    """
    entities: list[_ExtractedEntity] = []
    for pattern, entity_type in _NER_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(1)
            canonical = raw.lower().strip()
            if len(canonical) < 2:
                continue
            entities.append(
                _ExtractedEntity(
                    span_start=match.start(1),
                    span_end=match.end(1),
                    text=raw,
                    entity_type=entity_type,
                    canonical_name=canonical,
                )
            )
    # Stable sort: span_start ASC, entity_type ASC
    entities.sort(key=lambda e: (e.span_start, e.entity_type))
    return entities


def _edge_weight_from_distance(char_distance: int, window: int) -> float:
    """Compute relationship edge weight from character distance.

    Returns a value in (0.0, 1.0]: closer entities have higher weight.
    """
    if char_distance <= 0:
        return 1.0
    return max(0.0, 1.0 - char_distance / window)


class GraphIngestionPipeline:
    """Data Plane component that ingests CanonicalArtifacts into a KnowledgeGraph.

    Steps per artifact:
      1. Coherence-score the artifact text.
      2. Extract entities via deterministic NER.
      3. Upsert EntityNodes into the graph.
      4. Create a FragmentNode for the artifact.
      5. Add ContainsEdges from the FragmentNode to each EntityNode.
      6. Add RelationshipEdges (co_occurs) for entity pairs within the
         co-occurrence window.
    """

    def __init__(
        self,
        graph: KnowledgeGraph,
        co_occurrence_window: int = _CO_OCCURRENCE_WINDOW,
    ) -> None:
        """Initialize the pipeline.

        Args:
            graph: The KnowledgeGraph to populate.
            co_occurrence_window: Character window for co-occurrence edges.

        """
        self._graph = graph
        self._window = co_occurrence_window

    def ingest(self, artifact: CanonicalArtifact) -> list[str]:
        """Ingest a single CanonicalArtifact into the knowledge graph.

        Args:
            artifact: The canonicalized artifact to ingest.

        Returns:
            List of EntityNode IDs created or updated.

        """
        text = artifact.normalized_text or artifact.raw_text
        coherence = _decoder.score_coherence(text)

        # Step 2 — entity extraction
        entities = _extract_entities(text)

        # Step 3 — upsert EntityNodes
        entity_ids: list[str] = []
        for ent in entities:
            eid = _compute_entity_id(ent.entity_type, ent.canonical_name)
            node = EntityNode(
                id=eid,
                entity_type=ent.entity_type,
                canonical_name=ent.canonical_name,
                aliases=[ent.text] if ent.text.lower() != ent.canonical_name else [],
                provenance=[artifact.artifact_id],
                created_at=time.time(),
                version=GRAPH_SCHEMA_VERSION,
            )
            self._graph.upsert_entity(node)
            entity_ids.append(eid)

        # Step 4 — create FragmentNode
        frag_id = _compute_fragment_id(artifact.artifact_id, 0)
        frag_node = FragmentNode(
            id=frag_id,
            artifact_id=artifact.artifact_id,
            char_offset=0,
            text=text,
            meaning_hash=artifact.meaning_hash,
            coherence_score=coherence.overall_score,
            version=GRAPH_SCHEMA_VERSION,
        )
        self._graph.upsert_fragment(frag_node)

        # Step 5 — ContainsEdges
        for ent in entities:
            eid = _compute_entity_id(ent.entity_type, ent.canonical_name)
            contains = ContainsEdge(
                fragment_id=frag_id,
                entity_id=eid,
                span_start=ent.span_start,
                span_end=ent.span_end,
                version=GRAPH_SCHEMA_VERSION,
            )
            self._graph.add_contains(contains)

        # Step 6 — RelationshipEdges (co_occurs) for pairs within window
        for i, ent_a in enumerate(entities):
            for ent_b in entities[i + 1 :]:
                distance = abs(ent_b.span_start - ent_a.span_end)
                if distance > self._window:
                    continue
                weight = _edge_weight_from_distance(distance, self._window)
                id_a = _compute_entity_id(ent_a.entity_type, ent_a.canonical_name)
                id_b = _compute_entity_id(ent_b.entity_type, ent_b.canonical_name)
                self._graph.add_relationship(
                    RelationshipEdge(
                        source_id=id_a,
                        target_id=id_b,
                        relation_type="co_occurs",
                        weight=weight,
                        provenance=[artifact.artifact_id],
                        version=GRAPH_SCHEMA_VERSION,
                    )
                )

        return entity_ids
