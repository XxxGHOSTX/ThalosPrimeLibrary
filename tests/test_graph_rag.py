"""Tests for the GraphRAG add-on — deterministic graph and retrieval behaviour.

All tests are deterministic: no random seed is needed because all graph
operations are deterministic by construction.

Test coverage targets:
    * SimpleKnowledgeGraph full lifecycle.
    * add_node idempotency.
    * add_edge referential integrity (KeyError on missing node).
    * query_neighbors: depth 1, depth 2, relation filter.
    * find_path: existing and non-existing paths.
    * retrieve_context: score propagation and ordering.
    * HybridRetriever full lifecycle.
    * HybridRetriever.retrieve: graph hits, unknown query, top_k cap.
    * HybridRetriever checkpoint round-trip.
    * Protocol compliance via isinstance checks.
"""

from __future__ import annotations

import pytest

from thalos_prime.graph_rag.interfaces import (
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    RetrievalCandidate,
    Retriever,
)
from thalos_prime.graph_rag.retriever import HybridRetriever
from thalos_prime.graph_rag.simple_graph import SimpleKnowledgeGraph

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_graph() -> SimpleKnowledgeGraph:
    """A freshly initialized, validated SimpleKnowledgeGraph."""
    g = SimpleKnowledgeGraph()
    g.initialize()
    g.validate()
    return g


@pytest.fixture
def populated_graph() -> SimpleKnowledgeGraph:
    """A graph with a small deterministic knowledge base.

    Topology (directed):
        python   --[is_a]-->     language   (weight=1.0)
        python   --[used_for]--> ml         (weight=0.9)
        ml       --[part_of]-->  ai         (weight=0.8)
        ai       --[causes]-->   automation (weight=0.7)
        language --[is_a]-->     tool       (weight=0.6)
    """
    g = SimpleKnowledgeGraph()
    g.initialize()

    nodes = [
        GraphNode(node_id="python", label="Python Programming Language"),
        GraphNode(node_id="language", label="Programming Language"),
        GraphNode(node_id="ml", label="Machine Learning"),
        GraphNode(node_id="ai", label="Artificial Intelligence"),
        GraphNode(node_id="automation", label="Automation"),
        GraphNode(node_id="tool", label="Software Tool"),
    ]
    for node in nodes:
        g.add_node(node)

    edges = [
        GraphEdge("python", "language", "is_a", weight=1.0),
        GraphEdge("python", "ml", "used_for", weight=0.9),
        GraphEdge("ml", "ai", "part_of", weight=0.8),
        GraphEdge("ai", "automation", "causes", weight=0.7),
        GraphEdge("language", "tool", "is_a", weight=0.6),
    ]
    for edge in edges:
        g.add_edge(edge)

    g.validate()
    return g


@pytest.fixture
def retriever(populated_graph: SimpleKnowledgeGraph) -> HybridRetriever:
    """A HybridRetriever backed by the populated graph, fully lifecycle'd."""
    r = HybridRetriever(populated_graph)
    r.validate()
    r.operate()
    return r


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    def test_simple_graph_implements_knowledge_graph_protocol(
        self, empty_graph: SimpleKnowledgeGraph
    ) -> None:
        assert isinstance(empty_graph, KnowledgeGraph)

    def test_hybrid_retriever_implements_retriever_protocol(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.validate()
        r = HybridRetriever(g)
        assert isinstance(r, Retriever)


# ---------------------------------------------------------------------------
# SimpleKnowledgeGraph — lifecycle
# ---------------------------------------------------------------------------


class TestSimpleKnowledgeGraphLifecycle:
    def test_initialize_resets_state(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.add_node(GraphNode("x", "X"))
        assert g.node_count == 1
        g.initialize()  # second call resets
        assert g.node_count == 0

    def test_validate_returns_true_on_empty_graph(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        assert g.validate() is True

    def test_operate_raises_before_validate(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        with pytest.raises(RuntimeError, match="before validate"):
            g.operate()

    def test_operate_succeeds_after_validate(self, empty_graph: SimpleKnowledgeGraph) -> None:
        empty_graph.operate()  # should not raise

    def test_terminate_clears_state(self, populated_graph: SimpleKnowledgeGraph) -> None:
        assert populated_graph.node_count > 0
        populated_graph.terminate()
        assert populated_graph.node_count == 0
        assert populated_graph.edge_count == 0
        assert populated_graph.is_ready is False

    def test_reconcile_removes_orphan_nx_nodes(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.add_node(GraphNode("a", "A"))
        # Manually corrupt _nodes to simulate orphan in nx graph
        del g._nodes["a"]
        g.reconcile()
        assert g._graph.number_of_nodes() == 0

    def test_checkpoint_schema_version(self, populated_graph: SimpleKnowledgeGraph) -> None:
        snap = populated_graph.checkpoint()
        assert snap["schema_version"] == 1
        assert snap["node_count"] == 6
        assert snap["edge_count"] == 5

    def test_checkpoint_nodes_sorted(self, populated_graph: SimpleKnowledgeGraph) -> None:
        snap = populated_graph.checkpoint()
        nodes = snap["nodes"]
        assert isinstance(nodes, list)
        node_ids = [n["node_id"] for n in nodes]  # type: ignore[index]
        assert node_ids == sorted(node_ids)


# ---------------------------------------------------------------------------
# SimpleKnowledgeGraph — mutations
# ---------------------------------------------------------------------------


class TestSimpleKnowledgeGraphMutations:
    def test_add_node_basic(self, empty_graph: SimpleKnowledgeGraph) -> None:
        empty_graph.add_node(GraphNode("n1", "Node One"))
        assert empty_graph.node_count == 1

    def test_add_node_idempotent(self, empty_graph: SimpleKnowledgeGraph) -> None:
        node = GraphNode("n1", "Node One")
        empty_graph.add_node(node)
        empty_graph.add_node(node)  # second add — should be no-op
        assert empty_graph.node_count == 1

    def test_add_edge_missing_source_raises(self, empty_graph: SimpleKnowledgeGraph) -> None:
        empty_graph.add_node(GraphNode("target", "Target"))
        with pytest.raises(KeyError, match="source"):
            empty_graph.add_edge(GraphEdge("missing", "target", "rel"))

    def test_add_edge_missing_target_raises(self, empty_graph: SimpleKnowledgeGraph) -> None:
        empty_graph.add_node(GraphNode("source", "Source"))
        with pytest.raises(KeyError, match="target"):
            empty_graph.add_edge(GraphEdge("source", "missing", "rel"))

    def test_add_edge_increments_count(self, empty_graph: SimpleKnowledgeGraph) -> None:
        empty_graph.add_node(GraphNode("a", "A"))
        empty_graph.add_node(GraphNode("b", "B"))
        empty_graph.add_edge(GraphEdge("a", "b", "related"))
        assert empty_graph.edge_count == 1

    def test_validate_fails_on_bad_weight(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.add_node(GraphNode("a", "A"))
        g.add_node(GraphNode("b", "B"))
        # Inject invalid weight directly into nx graph
        g._graph.add_edge("a", "b", relation="x", weight=2.5)
        with pytest.raises(ValueError, match="weight"):
            g.validate()


# ---------------------------------------------------------------------------
# SimpleKnowledgeGraph — query_neighbors
# ---------------------------------------------------------------------------


class TestQueryNeighbors:
    def test_depth_1_returns_direct_neighbors(
        self, populated_graph: SimpleKnowledgeGraph
    ) -> None:
        neighbors = populated_graph.query_neighbors("python", max_depth=1)
        neighbor_ids = {n.node_id for n in neighbors}
        assert neighbor_ids == {"language", "ml"}

    def test_depth_2_returns_transitive_neighbors(
        self, populated_graph: SimpleKnowledgeGraph
    ) -> None:
        neighbors = populated_graph.query_neighbors("python", max_depth=2)
        neighbor_ids = {n.node_id for n in neighbors}
        # direct: language, ml  via language: tool  via ml: ai
        assert "tool" in neighbor_ids
        assert "ai" in neighbor_ids

    def test_relation_filter_is_a(self, populated_graph: SimpleKnowledgeGraph) -> None:
        neighbors = populated_graph.query_neighbors("python", relation="is_a", max_depth=1)
        neighbor_ids = {n.node_id for n in neighbors}
        assert neighbor_ids == {"language"}
        assert "ml" not in neighbor_ids

    def test_results_are_sorted_by_node_id(
        self, populated_graph: SimpleKnowledgeGraph
    ) -> None:
        neighbors = populated_graph.query_neighbors("python", max_depth=1)
        ids = [n.node_id for n in neighbors]
        assert ids == sorted(ids)

    def test_missing_node_raises(self, populated_graph: SimpleKnowledgeGraph) -> None:
        with pytest.raises(KeyError, match="not found"):
            populated_graph.query_neighbors("nonexistent")

    def test_isolated_node_returns_empty(self, empty_graph: SimpleKnowledgeGraph) -> None:
        empty_graph.add_node(GraphNode("lone", "Lone Node"))
        lone_neighbors = empty_graph.query_neighbors("lone")
        assert lone_neighbors == []


# ---------------------------------------------------------------------------
# SimpleKnowledgeGraph — find_path
# ---------------------------------------------------------------------------


class TestFindPath:
    def test_direct_path(self, populated_graph: SimpleKnowledgeGraph) -> None:
        path = populated_graph.find_path("python", "language")
        assert path == ["python", "language"]

    def test_multi_hop_path(self, populated_graph: SimpleKnowledgeGraph) -> None:
        path = populated_graph.find_path("python", "ai")
        # python -> ml -> ai
        assert path == ["python", "ml", "ai"]

    def test_no_path_returns_empty(self, populated_graph: SimpleKnowledgeGraph) -> None:
        # automation has no outgoing edges in the fixture
        path = populated_graph.find_path("automation", "python")
        assert path == []

    def test_missing_source_returns_empty(self, populated_graph: SimpleKnowledgeGraph) -> None:
        path = populated_graph.find_path("missing", "python")
        assert path == []

    def test_missing_target_returns_empty(self, populated_graph: SimpleKnowledgeGraph) -> None:
        path = populated_graph.find_path("python", "missing")
        assert path == []


# ---------------------------------------------------------------------------
# SimpleKnowledgeGraph — retrieve_context
# ---------------------------------------------------------------------------


class TestRetrieveContext:
    def test_returns_candidates_for_known_node(
        self, populated_graph: SimpleKnowledgeGraph
    ) -> None:
        candidates = populated_graph.retrieve_context("python", max_depth=1)
        assert len(candidates) > 0
        for c in candidates:
            assert isinstance(c, RetrievalCandidate)
            assert c.source == "graph"

    def test_unknown_node_returns_empty(
        self, populated_graph: SimpleKnowledgeGraph
    ) -> None:
        candidates = populated_graph.retrieve_context("unknown_entity")
        assert candidates == []

    def test_scores_sorted_descending(self, populated_graph: SimpleKnowledgeGraph) -> None:
        candidates = populated_graph.retrieve_context("python", max_depth=2)
        scores = [c.score for c in candidates]
        assert scores == sorted(scores, reverse=True)

    def test_depth_1_candidates_have_depth_metadata(
        self, populated_graph: SimpleKnowledgeGraph
    ) -> None:
        candidates = populated_graph.retrieve_context("python", max_depth=1)
        for c in candidates:
            assert c.metadata["depth"] == "1"

    def test_depth_2_includes_deeper_candidates(
        self, populated_graph: SimpleKnowledgeGraph
    ) -> None:
        d1 = populated_graph.retrieve_context("python", max_depth=1)
        d2 = populated_graph.retrieve_context("python", max_depth=2)
        assert len(d2) > len(d1)

    def test_deterministic_repeated_calls(
        self, populated_graph: SimpleKnowledgeGraph
    ) -> None:
        c1 = populated_graph.retrieve_context("python", max_depth=2)
        c2 = populated_graph.retrieve_context("python", max_depth=2)
        assert [c.content for c in c1] == [c.content for c in c2]
        assert [c.score for c in c1] == [c.score for c in c2]


# ---------------------------------------------------------------------------
# HybridRetriever — lifecycle
# ---------------------------------------------------------------------------


class TestHybridRetrieverLifecycle:
    def test_full_lifecycle(self) -> None:
        g = SimpleKnowledgeGraph()
        r = HybridRetriever(g)
        r.initialize()
        r.validate()
        r.operate()
        snap = r.checkpoint()
        assert snap["schema_version"] == 1
        assert snap["query_count"] == 0
        r.terminate()
        assert r.is_ready is False

    def test_validate_raises_on_invalid_graph(self) -> None:
        g = SimpleKnowledgeGraph()
        r = HybridRetriever(g)
        r.initialize()
        # Corrupt nx graph manually to force validation failure (orphan node)
        g._graph.add_node("orphan")
        with pytest.raises(ValueError, match="node count"):
            r.validate()

    def test_operate_raises_before_validate(self) -> None:
        g = SimpleKnowledgeGraph()
        r = HybridRetriever(g)
        r.initialize()
        with pytest.raises(RuntimeError, match="before validate"):
            r.operate()

    def test_checkpoint_includes_query_count(self, retriever: HybridRetriever) -> None:
        retriever.retrieve("python", top_k=3)
        snap = retriever.checkpoint()
        assert snap["query_count"] == 1

    def test_reconcile_delegates_to_graph(self, retriever: HybridRetriever) -> None:
        retriever.reconcile()  # should not raise


# ---------------------------------------------------------------------------
# HybridRetriever — retrieve
# ---------------------------------------------------------------------------


class TestHybridRetrieverRetrieve:
    def test_retrieve_known_entity_returns_candidates(
        self, retriever: HybridRetriever
    ) -> None:
        results = retriever.retrieve("python", top_k=10)
        assert len(results) > 0
        assert all(isinstance(r, RetrievalCandidate) for r in results)

    def test_retrieve_unknown_entity_returns_empty(
        self, retriever: HybridRetriever
    ) -> None:
        results = retriever.retrieve("unknown_entity_xyz", top_k=5)
        assert results == []

    def test_top_k_cap_is_enforced(self, retriever: HybridRetriever) -> None:
        results = retriever.retrieve("python", top_k=1)
        assert len(results) <= 1

    def test_results_sorted_by_score_descending(self, retriever: HybridRetriever) -> None:
        results = retriever.retrieve("python", top_k=10)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_invalid_top_k_raises(self, retriever: HybridRetriever) -> None:
        with pytest.raises(ValueError, match="top_k"):
            retriever.retrieve("python", top_k=0)

    def test_query_count_increments(self, retriever: HybridRetriever) -> None:
        initial = retriever.query_count
        retriever.retrieve("python")
        retriever.retrieve("ml")
        assert retriever.query_count == initial + 2

    def test_deterministic_results(self, retriever: HybridRetriever) -> None:
        r1 = retriever.retrieve("python", top_k=5)
        r2 = retriever.retrieve("python", top_k=5)
        assert [c.content for c in r1] == [c.content for c in r2]
        assert [c.score for c in r1] == [c.score for c in r2]

    def test_vector_stub_returns_empty(self) -> None:
        g = SimpleKnowledgeGraph()
        r = HybridRetriever(g)
        stub_result = r._vector_retrieve_stub("anything")
        assert stub_result == []

    def test_add_node_and_edge_via_retriever(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.validate()
        r = HybridRetriever(g)
        r.validate()
        r.operate()

        r.add_node(GraphNode("alpha", "Alpha"))
        r.add_node(GraphNode("beta", "Beta"))
        r.add_edge_to_graph("alpha", "beta", "related_to", weight=0.75)

        results = r.retrieve("alpha", top_k=5)
        assert len(results) == 1
        assert results[0].score == pytest.approx(0.75)
