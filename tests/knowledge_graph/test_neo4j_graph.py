"""Tests for Neo4jKnowledgeGraph layer."""

from __future__ import annotations

from thalos_prime.knowledge_graph.neo4j_graph import (
    CypherQuery,
    Neo4jKnowledgeGraph,
    NodeRecord,
    RelationshipRecord,
)


class TestNodeRecord:
    def test_default_fields(self) -> None:
        node = NodeRecord(node_id="n1")
        assert node.labels == set()
        assert node.properties == {}

    def test_to_dict(self) -> None:
        node = NodeRecord(node_id="n1", labels={"Person"}, properties={"name": "Alice"})
        d = node.to_dict()
        assert d["node_id"] == "n1"
        assert d["labels"] == ["Person"]
        assert d["properties"] == {"name": "Alice"}


class TestRelationshipRecord:
    def test_to_dict(self) -> None:
        rel = RelationshipRecord(
            source_id="a", target_id="b", rel_type="KNOWS", properties={"since": 2020},
        )
        d = rel.to_dict()
        assert d["source_id"] == "a"
        assert d["target_id"] == "b"
        assert d["rel_type"] == "KNOWS"
        assert d["properties"]["since"] == 2020


class TestCypherQuery:
    def test_to_dict(self) -> None:
        q = CypherQuery(operation="match_nodes", node_label="Person", limit=10)
        d = q.to_dict()
        assert d["operation"] == "match_nodes"
        assert d["node_label"] == "Person"
        assert d["limit"] == 10


class TestNeo4jKnowledgeGraph:
    def _make_graph(self) -> Neo4jKnowledgeGraph:
        g = Neo4jKnowledgeGraph(seed=42)
        g.initialize()
        return g

    def test_initialize_sets_initialized(self) -> None:
        g = self._make_graph()
        assert g._initialized is True
        assert g.node_count == 0

    def test_validate_fails_before_initialize(self) -> None:
        g = Neo4jKnowledgeGraph()
        result = g.validate()
        assert result.valid is False
        assert "not initialized" in result.message

    def test_validate_passes_after_initialize(self) -> None:
        g = self._make_graph()
        result = g.validate()
        assert result.valid is True

    def test_create_node(self) -> None:
        g = self._make_graph()
        node = g.create_node(NodeRecord(node_id="alice", labels={"Person"}, properties={"age": 30}))
        assert node.node_id == "alice"
        assert g.node_count == 1

    def test_get_node(self) -> None:
        g = self._make_graph()
        g.create_node(NodeRecord(node_id="bob", labels={"Person"}, properties={"age": 25}))
        result = g.get_node("bob")
        assert result is not None
        assert result.node_id == "bob"
        assert "Person" in result.labels
        assert result.properties["age"] == 25

    def test_get_node_not_found(self) -> None:
        g = self._make_graph()
        assert g.get_node("nonexistent") is None

    def test_delete_node(self) -> None:
        g = self._make_graph()
        g.create_node(NodeRecord(node_id="temp"))
        assert g.delete_node("temp") is True
        assert g.node_count == 0
        assert g.get_node("temp") is None

    def test_delete_node_not_found(self) -> None:
        g = self._make_graph()
        assert g.delete_node("nonexistent") is False

    def test_create_relationship(self) -> None:
        g = self._make_graph()
        g.create_node(NodeRecord(node_id="a"))
        g.create_node(NodeRecord(node_id="b"))
        rel = g.create_relationship(
            RelationshipRecord(source_id="a", target_id="b", rel_type="KNOWS"),
        )
        assert rel.rel_type == "KNOWS"
        assert g.relationship_count == 1

    def test_create_relationship_auto_creates_nodes(self) -> None:
        g = self._make_graph()
        g.create_relationship(
            RelationshipRecord(source_id="x", target_id="y", rel_type="LINKS"),
        )
        assert g.node_count == 2
        assert g.relationship_count == 1

    def test_get_relationships(self) -> None:
        g = self._make_graph()
        g.create_relationship(
            RelationshipRecord(source_id="a", target_id="b", rel_type="KNOWS"),
        )
        g.create_relationship(
            RelationshipRecord(source_id="a", target_id="c", rel_type="LIKES"),
        )
        rels = g.get_relationships("a")
        assert len(rels) == 2

    def test_get_relationships_filtered_by_type(self) -> None:
        g = self._make_graph()
        g.create_relationship(
            RelationshipRecord(source_id="a", target_id="b", rel_type="KNOWS"),
        )
        g.create_relationship(
            RelationshipRecord(source_id="a", target_id="c", rel_type="LIKES"),
        )
        rels = g.get_relationships("a", rel_type="KNOWS")
        assert len(rels) == 1
        assert rels[0].target_id == "b"

    def test_invalid_label_rejected(self) -> None:
        g = self._make_graph()
        import pytest
        with pytest.raises(ValueError, match="Invalid label"):
            g.create_node(NodeRecord(node_id="bad", labels={"invalid-label!"}))

    def test_match_nodes_by_label(self) -> None:
        g = self._make_graph()
        g.create_node(NodeRecord(node_id="a", labels={"Person"}))
        g.create_node(NodeRecord(node_id="b", labels={"Place"}))
        g.create_node(NodeRecord(node_id="c", labels={"Person"}))
        results = g.execute_query(CypherQuery(operation="match_nodes", node_label="Person"))
        assert len(results) == 2

    def test_match_nodes_by_properties(self) -> None:
        g = self._make_graph()
        g.create_node(NodeRecord(node_id="a", properties={"color": "red"}))
        g.create_node(NodeRecord(node_id="b", properties={"color": "blue"}))
        results = g.execute_query(
            CypherQuery(operation="match_nodes", properties={"color": "red"}),
        )
        assert len(results) == 1
        assert results[0]["node_id"] == "a"

    def test_match_relationships(self) -> None:
        g = self._make_graph()
        g.create_relationship(
            RelationshipRecord(source_id="a", target_id="b", rel_type="KNOWS"),
        )
        g.create_relationship(
            RelationshipRecord(source_id="c", target_id="d", rel_type="LIKES"),
        )
        results = g.execute_query(
            CypherQuery(operation="match_relationships", rel_type="KNOWS"),
        )
        assert len(results) == 1
        assert results[0]["rel_type"] == "KNOWS"

    def test_shortest_path(self) -> None:
        g = self._make_graph()
        g.create_relationship(
            RelationshipRecord(source_id="a", target_id="b", rel_type="R"),
        )
        g.create_relationship(
            RelationshipRecord(source_id="b", target_id="c", rel_type="R"),
        )
        results = g.execute_query(
            CypherQuery(operation="shortest_path", source_id="a", target_id="c"),
        )
        assert len(results) == 1
        assert results[0]["path"] == ["a", "b", "c"]
        assert results[0]["length"] == 2

    def test_shortest_path_no_path(self) -> None:
        g = self._make_graph()
        g.create_node(NodeRecord(node_id="a"))
        g.create_node(NodeRecord(node_id="z"))
        results = g.execute_query(
            CypherQuery(operation="shortest_path", source_id="a", target_id="z"),
        )
        assert results == []

    def test_neighbors(self) -> None:
        g = self._make_graph()
        g.create_relationship(
            RelationshipRecord(source_id="a", target_id="b", rel_type="R"),
        )
        g.create_relationship(
            RelationshipRecord(source_id="a", target_id="c", rel_type="R"),
        )
        results = g.execute_query(
            CypherQuery(operation="neighbors", source_id="a"),
        )
        assert len(results) == 2

    def test_query_count_increments(self) -> None:
        g = self._make_graph()
        assert g.query_count == 0
        g.execute_query(CypherQuery(operation="match_nodes"))
        g.execute_query(CypherQuery(operation="match_nodes"))
        assert g.query_count == 2

    def test_operate_does_not_raise(self) -> None:
        g = self._make_graph()
        g.operate()

    def test_reconcile_fixes_counts(self) -> None:
        g = self._make_graph()
        g.create_node(NodeRecord(node_id="a"))
        g._node_count = 999
        g.reconcile()
        assert g._node_count == 1

    def test_checkpoint_returns_dict(self) -> None:
        g = self._make_graph()
        g.create_node(NodeRecord(node_id="a", labels={"X"}))
        g.create_relationship(
            RelationshipRecord(source_id="a", target_id="b", rel_type="R"),
        )
        state = g.checkpoint()
        assert isinstance(state, dict)
        assert state["component"] == "Neo4jKnowledgeGraph"
        assert "nodes" in state
        assert "relationships" in state

    def test_terminate_resets_state(self) -> None:
        g = self._make_graph()
        g.create_node(NodeRecord(node_id="a"))
        g.terminate()
        assert g._initialized is False
        assert g.node_count == 0
        assert g.relationship_count == 0

    def test_lifecycle_events_recorded(self) -> None:
        g = self._make_graph()
        g.operate()
        g.checkpoint()
        g.terminate()
        events = g.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "operate" in methods
        assert "checkpoint" in methods
        assert "terminate" in methods

    def test_delete_node_removes_edges(self) -> None:
        g = self._make_graph()
        g.create_relationship(
            RelationshipRecord(source_id="a", target_id="b", rel_type="R"),
        )
        g.create_relationship(
            RelationshipRecord(source_id="b", target_id="c", rel_type="R"),
        )
        assert g.relationship_count == 2
        g.delete_node("b")
        assert g.relationship_count == 0

    def test_update_existing_node(self) -> None:
        g = self._make_graph()
        g.create_node(NodeRecord(node_id="a", properties={"v": 1}))
        g.create_node(NodeRecord(node_id="a", properties={"v": 2}))
        assert g.node_count == 1
        node = g.get_node("a")
        assert node is not None
        assert node.properties["v"] == 2
