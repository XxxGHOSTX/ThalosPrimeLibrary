"""Tests for GraphRAGRetriever."""

from __future__ import annotations

from thalos_prime.library_of_sense.retrieval.graph_rag import GraphRAGRetriever
from thalos_prime.library_of_sense.retrieval.knowledge_graph import GraphTriple


def _simple_extractor(text: str) -> list[GraphTriple]:
    """Extract simple triples by splitting on whitespace."""
    words = text.split()
    return [
        GraphTriple(subject=words[i], predicate=words[i + 1], obj=words[i + 2])
        for i in range(0, len(words) - 2, 3)
    ]


class TestGraphRAGRetriever:
    def test_initialize_sets_initialized(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        assert retriever._initialized is True

    def test_validate_fails_before_initialize(self) -> None:
        retriever = GraphRAGRetriever()
        result = retriever.validate()
        assert result.valid is False
        assert "not initialized" in result.message

    def test_validate_passes_after_initialize(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        result = retriever.validate()
        assert result.valid is True

    def test_operate_logs_statistics(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        retriever.operate()  # Should not raise

    def test_reconcile_clears_cache(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        retriever._kg.add_triple(GraphTriple("A", "is", "B"))
        retriever.retrieve("A")
        assert len(retriever._query_cache) > 0
        retriever.reconcile()
        assert retriever._query_cache == {}

    def test_checkpoint_returns_dict(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        state = retriever.checkpoint()
        assert isinstance(state, dict)
        assert state["component"] == "GraphRAGRetriever"
        assert "triple_count" in state.get("kg", {})  # type: ignore[operator]

    def test_terminate_clears_state(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        retriever._kg.add_triple(GraphTriple("X", "y", "Z"))
        retriever.terminate()
        assert retriever._initialized is False
        assert retriever._indexed_documents == []
        assert retriever._query_cache == {}

    def test_index_document_returns_triple_count(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        # "A is B" = 1 triple (exactly 3 words)
        count = retriever.index_document("A is B", _simple_extractor)
        assert count == 1
        # "A is B C has D" = 2 triples
        count2 = retriever.index_document("A is B C has D", _simple_extractor)
        assert count2 == 2

    def test_index_document_adds_to_kg(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        retriever.index_document("Python is language", _simple_extractor)
        triples = retriever._kg.query_subject("Python")
        assert len(triples) == 1
        assert triples[0].predicate == "is"

    def test_retrieve_returns_results(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        retriever._kg.add_triple(GraphTriple("cat", "is_a", "animal", confidence=0.9))
        results = retriever.retrieve("cat")
        assert len(results) >= 1
        assert any(r.confidence > 0 for r in results)

    def test_retrieve_empty_for_unknown_entity(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        results = retriever.retrieve("unknown_xyz_entity")
        assert results == []

    def test_retrieve_top_k_limits_results(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        for i in range(10):
            retriever._kg.add_triple(GraphTriple("root", f"rel_{i}", f"obj_{i}"))
        results = retriever.retrieve("root", top_k=3)
        assert len(results) <= 3

    def test_retrieve_uses_cache_on_second_call(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        retriever._kg.add_triple(GraphTriple("A", "b", "C"))
        results_first = retriever.retrieve("A")
        results_second = retriever.retrieve("A")
        assert results_first == results_second

    def test_retrieve_sorted_by_confidence_descending(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        retriever._kg.add_triple(GraphTriple("A", "r1", "B", confidence=0.5))
        retriever._kg.add_triple(GraphTriple("A", "r2", "C", confidence=0.9))
        results = retriever.retrieve("A", top_k=10)
        for i in range(len(results) - 1):
            assert results[i].confidence >= results[i + 1].confidence

    def test_get_context_window_single_hop(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        retriever._kg.add_triple(GraphTriple("A", "b", "B"))
        retriever._kg.add_triple(GraphTriple("B", "c", "C"))
        triples = retriever.get_context_window("A", hops=1)
        subjects = [t.subject for t in triples]
        assert "A" in subjects
        assert "B" not in subjects  # only 1 hop

    def test_get_context_window_two_hops(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        retriever._kg.add_triple(GraphTriple("A", "b", "B"))
        retriever._kg.add_triple(GraphTriple("B", "c", "C"))
        triples = retriever.get_context_window("A", hops=2)
        subjects = {t.subject for t in triples}
        assert "A" in subjects
        assert "B" in subjects

    def test_lifecycle_events_recorded(self) -> None:
        retriever = GraphRAGRetriever()
        retriever.initialize()
        retriever.operate()
        retriever.checkpoint()
        retriever.terminate()
        events = retriever.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "checkpoint" in methods
        assert "terminate" in methods
