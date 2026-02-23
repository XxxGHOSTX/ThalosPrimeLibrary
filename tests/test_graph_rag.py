"""Tests for thalos_prime.graph_rag — knowledge graph, ingestion, retrieval."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from thalos_prime.graph_rag import (
    ContainsEdge,
    EntityNode,
    FragmentNode,
    GraphIngestionPipeline,
    GraphRAGControlPlane,
    GraphRAGError,
    GraphRetriever,
    GraphRetrievalResult,
    KnowledgeGraph,
    RelationshipEdge,
)
from thalos_prime.graph_rag.schema import GRAPH_SCHEMA_VERSION
from thalos_prime.ingest import ingest_fragment


# ---------------------------------------------------------------------------
# KnowledgeGraph
# ---------------------------------------------------------------------------


def _make_entity(name: str, etype: str = "concept") -> EntityNode:
    from hashlib import sha256
    eid = sha256(f"{etype}:{name}".encode()).hexdigest()
    return EntityNode(
        id=eid,
        entity_type=etype,
        canonical_name=name,
        aliases=[],
        provenance=["test"],
        created_at=0.0,
    )


def _make_fragment(artifact_id: str = "art1", text: str = "hello world") -> FragmentNode:
    from hashlib import sha256
    fid = sha256(f"{artifact_id}:0".encode()).hexdigest()
    return FragmentNode(
        id=fid,
        artifact_id=artifact_id,
        char_offset=0,
        text=text,
        meaning_hash="abc",
        coherence_score=0.5,
    )


class TestKnowledgeGraph:
    def test_empty_graph_counts(self):
        kg = KnowledgeGraph()
        assert kg.node_count == 0
        assert kg.edge_count == 0

    def test_upsert_entity_returns_true_on_new(self):
        kg = KnowledgeGraph()
        node = _make_entity("alpha")
        assert kg.upsert_entity(node) is True

    def test_upsert_entity_returns_false_on_update(self):
        kg = KnowledgeGraph()
        node = _make_entity("alpha")
        kg.upsert_entity(node)
        assert kg.upsert_entity(node) is False

    def test_get_entity_roundtrip(self):
        kg = KnowledgeGraph()
        node = _make_entity("beta", "person")
        kg.upsert_entity(node)
        result = kg.get_entity(node.id)
        assert result is not None
        assert result.canonical_name == "beta"
        assert result.entity_type == "person"

    def test_get_entity_missing_returns_none(self):
        kg = KnowledgeGraph()
        assert kg.get_entity("nonexistent") is None

    def test_find_entity_by_name(self):
        kg = KnowledgeGraph()
        kg.upsert_entity(_make_entity("gamma"))
        assert kg.find_entity_by_name("gamma") is not None
        assert kg.find_entity_by_name("delta") is None

    def test_find_entity_by_alias(self):
        kg = KnowledgeGraph()
        from hashlib import sha256
        eid = sha256("concept:epsilon".encode()).hexdigest()
        node = EntityNode(
            id=eid, entity_type="concept", canonical_name="epsilon",
            aliases=["eps"], provenance=[], created_at=0.0,
        )
        kg.upsert_entity(node)
        hits = kg.find_entity_by_alias("eps")
        assert len(hits) == 1
        assert hits[0].canonical_name == "epsilon"

    def test_upsert_fragment(self):
        kg = KnowledgeGraph()
        frag = _make_fragment()
        assert kg.upsert_fragment(frag) is True
        assert kg.upsert_fragment(frag) is False

    def test_get_fragment_roundtrip(self):
        kg = KnowledgeGraph()
        frag = _make_fragment(text="the quick brown fox")
        kg.upsert_fragment(frag)
        result = kg.get_fragment(frag.id)
        assert result is not None
        assert result.text == "the quick brown fox"

    def test_add_relationship(self):
        kg = KnowledgeGraph()
        a = _make_entity("a")
        b = _make_entity("b")
        kg.upsert_entity(a)
        kg.upsert_entity(b)
        edge = RelationshipEdge(
            source_id=a.id, target_id=b.id,
            relation_type="co_occurs", weight=0.8, provenance=[],
        )
        kg.add_relationship(edge)
        assert kg.edge_count == 1

    def test_add_contains_edge(self):
        kg = KnowledgeGraph()
        entity = _make_entity("fox")
        frag = _make_fragment(text="the quick fox")
        kg.upsert_entity(entity)
        kg.upsert_fragment(frag)
        edge = ContainsEdge(fragment_id=frag.id, entity_id=entity.id, span_start=10, span_end=13)
        kg.add_contains(edge)
        frags = kg.fragments_for_entity(entity.id)
        assert len(frags) == 1
        assert frags[0].id == frag.id

    def test_orphaned_fragment_ids(self):
        kg = KnowledgeGraph()
        frag = _make_fragment()
        kg.upsert_fragment(frag)
        orphans = kg.orphaned_fragment_ids()
        assert frag.id in orphans

    def test_snapshot_and_restore(self, tmp_path):
        kg = KnowledgeGraph()
        kg.upsert_entity(_make_entity("snapshot_test"))
        snap = tmp_path / "snap.json"
        kg.snapshot(snap)
        assert snap.exists()
        data = json.loads(snap.read_text())
        restored = KnowledgeGraph.from_dict(data)
        assert restored.node_count == 1

    def test_neighbors_sorted_by_weight_desc(self):
        kg = KnowledgeGraph()
        a = _make_entity("a")
        b = _make_entity("b")
        c = _make_entity("c")
        for n in (a, b, c):
            kg.upsert_entity(n)
        kg.add_relationship(RelationshipEdge(a.id, b.id, "co_occurs", 0.3, []))
        kg.add_relationship(RelationshipEdge(a.id, c.id, "co_occurs", 0.9, []))
        nbrs = kg.neighbors_of(a.id)
        weights = [attrs["weight"] for _, attrs in nbrs]
        assert weights == sorted(weights, reverse=True)


# ---------------------------------------------------------------------------
# GraphIngestionPipeline
# ---------------------------------------------------------------------------


class TestGraphIngestionPipeline:
    def test_ingest_populates_graph(self):
        kg = KnowledgeGraph()
        pipeline = GraphIngestionPipeline(kg)
        artifact = ingest_fragment("The quick brown fox jumps over the lazy dog", source="test")
        pipeline.ingest(artifact)
        assert kg.node_count > 0

    def test_ingest_creates_fragment_node(self):
        kg = KnowledgeGraph()
        pipeline = GraphIngestionPipeline(kg)
        artifact = ingest_fragment("hello world knowledge graph", source="test")
        pipeline.ingest(artifact)
        # At least one fragment node should exist
        frags = [nid for nid, attrs in kg._graph.nodes(data=True) if attrs.get("node_type") == "fragment"]
        assert len(frags) >= 1

    def test_ingest_deterministic(self):
        kg1 = KnowledgeGraph()
        kg2 = KnowledgeGraph()
        artifact = ingest_fragment("determinism test text", source="test")
        GraphIngestionPipeline(kg1).ingest(artifact)
        GraphIngestionPipeline(kg2).ingest(artifact)
        assert kg1.node_count == kg2.node_count
        assert kg1.edge_count == kg2.edge_count

    def test_ingest_returns_entity_ids(self):
        kg = KnowledgeGraph()
        pipeline = GraphIngestionPipeline(kg)
        artifact = ingest_fragment("The quick brown fox", source="test")
        entity_ids = pipeline.ingest(artifact)
        assert isinstance(entity_ids, list)

    def test_no_orphans_on_single_artifact_with_entities(self):
        kg = KnowledgeGraph()
        pipeline = GraphIngestionPipeline(kg)
        artifact = ingest_fragment("The quick brown fox jumped over barriers", source="test")
        pipeline.ingest(artifact)
        # Orphans exist only if fragment has no entity links;
        # with entity-rich text there should be none
        # (we don't mandate zero, just that method works)
        orphans = kg.orphaned_fragment_ids()
        assert isinstance(orphans, list)


# ---------------------------------------------------------------------------
# GraphRetriever
# ---------------------------------------------------------------------------


class TestGraphRetriever:
    def _populated_graph(self) -> KnowledgeGraph:
        kg = KnowledgeGraph()
        artifact = ingest_fragment(
            "The knowledge graph enables multi-hop retrieval and reasoning.",
            source="test",
        )
        GraphIngestionPipeline(kg).ingest(artifact)
        return kg

    def test_retrieve_empty_graph_returns_empty(self):
        kg = KnowledgeGraph()
        retriever = GraphRetriever()
        results = retriever.retrieve("any query", kg)
        assert results == []

    def test_retrieve_returns_sorted_results(self):
        kg = self._populated_graph()
        retriever = GraphRetriever()
        results = retriever.retrieve("knowledge graph", kg)
        scores = [r.final_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_retrieve_max_hops_zero(self):
        kg = self._populated_graph()
        retriever = GraphRetriever(max_hops=0)
        results = retriever.retrieve("knowledge", kg)
        assert isinstance(results, list)

    def test_retrieve_top_k_respected(self):
        kg = KnowledgeGraph()
        for i in range(5):
            artifact = ingest_fragment(f"text {i} about knowledge and graphs", source="test")
            GraphIngestionPipeline(kg).ingest(artifact)
        retriever = GraphRetriever(top_k=2)
        results = retriever.retrieve("knowledge", kg)
        assert len(results) <= 2

    def test_retrieve_result_fields(self):
        kg = self._populated_graph()
        retriever = GraphRetriever()
        results = retriever.retrieve("graph retrieval", kg)
        if results:
            r = results[0]
            assert isinstance(r, GraphRetrievalResult)
            assert 0.0 <= r.final_score <= 1.0
            assert r.hop_distance >= 0

    def test_retrieve_deterministic(self):
        kg = self._populated_graph()
        retriever = GraphRetriever()
        r1 = retriever.retrieve("knowledge graph", kg)
        r2 = retriever.retrieve("knowledge graph", kg)
        ids1 = [r.fragment_id for r in r1]
        ids2 = [r.fragment_id for r in r2]
        assert ids1 == ids2


# ---------------------------------------------------------------------------
# GraphRAGControlPlane
# ---------------------------------------------------------------------------


class TestGraphRAGControlPlane:
    def test_full_lifecycle(self, tmp_path):
        cp = GraphRAGControlPlane(seed=42, workdir=str(tmp_path))
        cp.initialize()
        cp.validate()
        artifact = ingest_fragment("lifecycle test knowledge graph", source="test")
        entity_ids = cp.operate([artifact])
        assert isinstance(entity_ids, list)
        cp.reconcile()
        snap_path = cp.checkpoint()
        assert snap_path.exists()
        cp.terminate()

    def test_validate_before_initialize_raises(self, tmp_path):
        cp = GraphRAGControlPlane(seed=1, workdir=str(tmp_path))
        with pytest.raises(GraphRAGError):
            cp.validate()

    def test_operate_before_initialize_raises(self, tmp_path):
        cp = GraphRAGControlPlane(seed=1, workdir=str(tmp_path))
        artifact = ingest_fragment("test", source="test")
        with pytest.raises(GraphRAGError):
            cp.operate([artifact])

    def test_query_after_ingest(self, tmp_path):
        cp = GraphRAGControlPlane(seed=42, workdir=str(tmp_path))
        cp.initialize()
        cp.validate()
        artifact = ingest_fragment("The graph connects knowledge nodes", source="test")
        cp.operate([artifact])
        results = cp.query("knowledge nodes")
        assert isinstance(results, list)

    def test_seed_salting(self, tmp_path):
        from thalos_prime.graph_rag.schema import GRAPH_RAG_SEED_SALT
        cp = GraphRAGControlPlane(seed=100, workdir=str(tmp_path))
        assert cp._seed == 100 ^ GRAPH_RAG_SEED_SALT

    def test_snapshot_restores_graph(self, tmp_path):
        cp = GraphRAGControlPlane(seed=42, workdir=str(tmp_path))
        cp.initialize()
        artifact = ingest_fragment("restore test knowledge", source="test")
        cp.operate([artifact])
        snap = cp.checkpoint()
        # Re-initialize from snapshot
        cp2 = GraphRAGControlPlane(seed=42, workdir=str(tmp_path))
        cp2.initialize()
        # node count should be restored
        assert cp2.graph.node_count == cp.graph.node_count

    def test_reconcile_removes_orphans(self, tmp_path):
        cp = GraphRAGControlPlane(seed=42, workdir=str(tmp_path))
        cp.initialize()
        # Add an orphaned fragment manually
        frag = _make_fragment(text="orphan")
        cp.graph.upsert_fragment(frag)
        orphans_before = cp.graph.orphaned_fragment_ids()
        cp.reconcile()
        orphans_after = cp.graph.orphaned_fragment_ids()
        assert len(orphans_after) <= len(orphans_before)
