"""Tests for Graph-RAG subsystem (SimpleKnowledgeGraph and HybridRetriever)."""

from __future__ import annotations

from thalos_prime.graph_rag.interfaces import GraphEdge, GraphNode
from thalos_prime.graph_rag.retriever import HybridRetriever
from thalos_prime.graph_rag.simple_graph import SimpleKnowledgeGraph


class TestSimpleKnowledgeGraph:
    def test_initialize_sets_initialized(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        assert g._initialized is True

    def test_validate_fails_before_initialize(self) -> None:
        g = SimpleKnowledgeGraph()
        result = g.validate()
        assert result.valid is False
        assert "not initialized" in result.message

    def test_validate_passes_after_initialize(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        result = g.validate()
        assert result.valid is True

    def test_add_node(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.add_node(GraphNode(node_id="a", label="Person"))
        assert g.node_count() == 1

    def test_add_edge_creates_nodes(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.add_edge(GraphEdge(source="a", target="b", relation="knows"))
        assert g.node_count() == 2
        assert g.edge_count() == 1

    def test_query_neighbors_one_hop(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.add_edge(GraphEdge(source="a", target="b", relation="knows"))
        g.add_edge(GraphEdge(source="b", target="c", relation="likes"))
        result = g.query_neighbors("a", hops=1)
        node_ids = {n.node_id for n in result.nodes}
        assert "a" in node_ids
        assert "b" in node_ids

    def test_query_neighbors_two_hops(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.add_edge(GraphEdge(source="a", target="b", relation="knows"))
        g.add_edge(GraphEdge(source="b", target="c", relation="likes"))
        result = g.query_neighbors("a", hops=2)
        node_ids = {n.node_id for n in result.nodes}
        assert "c" in node_ids

    def test_query_neighbors_missing_node(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        result = g.query_neighbors("nonexistent", hops=1)
        assert len(result.nodes) == 0
        assert len(result.edges) == 0

    def test_reconcile_prunes_dangling_edges(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.add_edge(GraphEdge(source="a", target="b", relation="r"))
        # Remove node 'b' manually to create a dangling edge
        del g._nodes["b"]
        g.reconcile()
        assert g.edge_count() == 0

    def test_checkpoint_returns_dict(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.add_node(GraphNode(node_id="x"))
        state = g.checkpoint()
        assert isinstance(state, dict)
        assert state["node_count"] == 1

    def test_terminate_clears_state(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.add_node(GraphNode(node_id="x"))
        g.terminate()
        assert g._initialized is False
        assert g.node_count() == 0

    def test_operate_does_not_raise(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.operate()

    def test_lifecycle_events_recorded(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.operate()
        g.checkpoint()
        g.terminate()
        events = g.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "terminate" in methods

    def test_node_replacement(self) -> None:
        g = SimpleKnowledgeGraph()
        g.initialize()
        g.add_node(GraphNode(node_id="a", label="v1"))
        g.add_node(GraphNode(node_id="a", label="v2"))
        assert g.node_count() == 1
        assert g._nodes["a"].label == "v2"


class TestHybridRetriever:
    def test_initialize_sets_initialized(self) -> None:
        r = HybridRetriever()
        r.initialize()
        assert r._initialized is True

    def test_validate_fails_before_initialize(self) -> None:
        r = HybridRetriever()
        result = r.validate()
        assert result.valid is False

    def test_validate_passes_after_initialize(self) -> None:
        r = HybridRetriever()
        r.initialize()
        result = r.validate()
        assert result.valid is True

    def test_add_node_and_edge(self) -> None:
        r = HybridRetriever()
        r.initialize()
        r.add_node(GraphNode(node_id="a"))
        r.add_edge(GraphEdge(source="a", target="b", relation="knows"))
        result = r.retrieve("a")
        assert result.graph_result is not None

    def test_index_text_and_retrieve(self) -> None:
        r = HybridRetriever()
        r.initialize()
        r.index_text("python programming language")
        result = r.retrieve("python")
        assert len(result.text_matches) > 0
        assert result.text_matches[0].confidence > 0

    def test_retrieve_increments_query_count(self) -> None:
        r = HybridRetriever()
        r.initialize()
        r.retrieve("test")
        r.retrieve("test")
        assert r._query_count == 2

    def test_combined_score(self) -> None:
        r = HybridRetriever()
        r.initialize()
        r.add_edge(GraphEdge(source="python", target="language", relation="is_a"))
        r.index_text("python is a programming language")
        result = r.retrieve("python")
        assert result.combined_score >= 0.0

    def test_checkpoint_returns_dict(self) -> None:
        r = HybridRetriever()
        r.initialize()
        state = r.checkpoint()
        assert isinstance(state, dict)
        assert state["component"] == "HybridRetriever"

    def test_terminate_clears_state(self) -> None:
        r = HybridRetriever()
        r.initialize()
        r.index_text("test")
        r.terminate()
        assert r._initialized is False

    def test_reconcile_does_not_raise(self) -> None:
        r = HybridRetriever()
        r.initialize()
        r.reconcile()

    def test_operate_does_not_raise(self) -> None:
        r = HybridRetriever()
        r.initialize()
        r.operate()

    def test_lifecycle_events_recorded(self) -> None:
        r = HybridRetriever()
        r.initialize()
        r.operate()
        r.checkpoint()
        r.terminate()
        events = r.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "terminate" in methods

    def test_hybrid_result_to_dict(self) -> None:
        r = HybridRetriever()
        r.initialize()
        r.add_edge(GraphEdge(source="a", target="b", relation="r"))
        r.index_text("a test document")
        result = r.retrieve("a")
        d = result.to_dict()
        assert "graph_result" in d
        assert "text_matches" in d
        assert "combined_score" in d
