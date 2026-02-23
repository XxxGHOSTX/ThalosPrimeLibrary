"""Tests for Library of Sense retrieval components."""

from __future__ import annotations

import pytest

from thalos_prime.library_of_sense.core.interfaces import QueryContext, QueryDomain
from thalos_prime.library_of_sense.retrieval.code_search import CodeSearchRetriever
from thalos_prime.library_of_sense.retrieval.computational import ComputationalRetriever
from thalos_prime.library_of_sense.retrieval.knowledge_graph import (
    GraphTriple,
    KnowledgeGraphRetriever,
)
from thalos_prime.library_of_sense.retrieval.multi_source import MultiSourceRetriever
from thalos_prime.library_of_sense.retrieval.web_retrieval import WebRetrievalHandler

# ---------------------------------------------------------------------------
# MultiSourceRetriever
# ---------------------------------------------------------------------------


class TestMultiSourceRetriever:
    def test_empty_sources_returns_empty_list(self) -> None:
        retriever = MultiSourceRetriever()
        ctx = QueryContext()
        assert retriever.query_all("test", ctx) == []

    def test_source_count_increments_on_add(self) -> None:
        retriever = MultiSourceRetriever()
        kg = KnowledgeGraphRetriever()
        retriever.add_source(kg)
        assert retriever.source_count() == 1

    def test_query_all_returns_sorted_by_confidence(self) -> None:
        retriever = MultiSourceRetriever()
        comp = ComputationalRetriever()
        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        retriever.add_source(comp)
        retriever.add_source(kg)
        ctx = QueryContext(domain=QueryDomain.COMPUTATIONAL)
        results = retriever.query_all("1 + 1", ctx)
        for i in range(len(results) - 1):
            assert results[i].confidence >= results[i + 1].confidence

    def test_min_confidence_filters_results(self) -> None:
        retriever = MultiSourceRetriever(min_confidence=0.5)
        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        retriever.add_source(kg)
        ctx = QueryContext()
        results = retriever.query_all("unknown_entity", ctx)
        assert all(r.confidence >= 0.5 for r in results)

    def test_validate_sources_returns_validation_results(self) -> None:
        retriever = MultiSourceRetriever()
        kg = KnowledgeGraphRetriever()
        retriever.add_source(kg)
        results = retriever.validate_sources()
        assert len(results) == 1
        assert results[0].valid is True


# ---------------------------------------------------------------------------
# WebRetrievalHandler
# ---------------------------------------------------------------------------


class TestWebRetrievalHandler:
    def test_initialize_sets_session(self) -> None:
        handler = WebRetrievalHandler()
        handler.initialize()
        result = handler.validate_source()
        assert result.valid is True
        handler.terminate()

    def test_validate_fails_before_initialize(self) -> None:
        handler = WebRetrievalHandler()
        with pytest.raises(RuntimeError):
            handler.validate()

    def test_validate_passes_after_initialize(self) -> None:
        handler = WebRetrievalHandler()
        handler.initialize()
        handler.validate()
        handler.terminate()

    def test_operate_logs_state(self) -> None:
        handler = WebRetrievalHandler()
        handler.initialize()
        handler.operate()
        handler.terminate()

    def test_reconcile_recreates_session_if_missing(self) -> None:
        handler = WebRetrievalHandler()
        handler.reconcile()
        result = handler.validate_source()
        assert result.valid is True
        handler.terminate()

    def test_checkpoint_logs_without_error(self) -> None:
        handler = WebRetrievalHandler()
        handler.initialize()
        handler.checkpoint()
        handler.terminate()

    def test_terminate_clears_session(self) -> None:
        handler = WebRetrievalHandler()
        handler.initialize()
        handler.terminate()
        result = handler.validate_source()
        assert result.valid is False

    def test_query_non_url_returns_empty_result(self) -> None:
        handler = WebRetrievalHandler()
        handler.initialize()
        ctx = QueryContext()
        result = handler.query("not a url", ctx)
        assert result.content == ""
        assert result.confidence == 0.0
        handler.terminate()

    def test_validate_source_before_init_returns_invalid(self) -> None:
        handler = WebRetrievalHandler()
        result = handler.validate_source()
        assert result.valid is False


# ---------------------------------------------------------------------------
# KnowledgeGraphRetriever
# ---------------------------------------------------------------------------


class TestKnowledgeGraphRetriever:
    def test_add_triple_increments_count(self) -> None:
        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        kg.add_triple(GraphTriple(subject="A", predicate="is", obj="B"))
        assert kg.triple_count == 1

    def test_query_subject_returns_triples(self) -> None:
        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        kg.add_triple(GraphTriple(subject="Python", predicate="is", obj="language"))
        triples = kg.query_subject("Python")
        assert len(triples) == 1
        assert triples[0].predicate == "is"

    def test_query_subject_unknown_entity_returns_empty(self) -> None:
        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        assert kg.query_subject("nonexistent") == []

    def test_find_path_existing(self) -> None:
        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        kg.add_triple(GraphTriple(subject="A", predicate="leads_to", obj="B"))
        kg.add_triple(GraphTriple(subject="B", predicate="leads_to", obj="C"))
        path = kg.find_path("A", "C")
        assert path == ["A", "B", "C"]

    def test_find_path_no_path_returns_empty(self) -> None:
        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        kg.add_triple(GraphTriple(subject="X", predicate="is", obj="Y"))
        path = kg.find_path("X", "Z")
        assert path == []

    def test_query_entity_found(self) -> None:
        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        kg.add_triple(GraphTriple(subject="math", predicate="includes", obj="algebra"))
        ctx = QueryContext()
        result = kg.query("math", ctx)
        assert result.confidence > 0
        assert "math" in result.content

    def test_query_entity_not_found(self) -> None:
        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        ctx = QueryContext()
        result = kg.query("unknown", ctx)
        assert result.confidence == 0.0
        assert result.content == ""

    def test_validate_returns_valid(self) -> None:
        kg = KnowledgeGraphRetriever()
        result = kg.validate()
        assert result.valid is True

    def test_data_ops_raise_when_not_operating(self) -> None:
        kg = KnowledgeGraphRetriever()
        ctx = QueryContext()
        with pytest.raises(RuntimeError):
            kg.add_triple(GraphTriple(subject="A", predicate="is", obj="B"))
        with pytest.raises(RuntimeError):
            kg.query_subject("A")
        with pytest.raises(RuntimeError):
            kg.find_path("A", "B")
        with pytest.raises(RuntimeError):
            kg.query("A", ctx)

    def test_lifecycle_sequence(self) -> None:
        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        kg.add_triple(GraphTriple(subject="X", predicate="rel", obj="Y"))
        assert kg.triple_count == 1
        kg.checkpoint()
        # After checkpoint, state returns to READY; re-enter OPERATING
        kg.operate()
        assert kg.triple_count == 1
        kg.terminate()
        assert kg.triple_count == 0


# ---------------------------------------------------------------------------
# CodeSearchRetriever
# ---------------------------------------------------------------------------


class TestCodeSearchRetriever:
    _SAMPLE_SOURCE = '''
def greet(name):
    """Greet someone by name."""
    return f"Hello, {name}"

class Greeter:
    """A greeter class."""
    pass
'''

    def test_index_source_valid(self) -> None:
        retriever = CodeSearchRetriever()
        count = retriever.index_source(self._SAMPLE_SOURCE, "test.py")
        assert count >= 2

    def test_index_source_invalid_syntax_returns_zero(self) -> None:
        retriever = CodeSearchRetriever()
        count = retriever.index_source("def invalid(:", "bad.py")
        assert count == 0

    def test_search_finds_by_name(self) -> None:
        retriever = CodeSearchRetriever()
        retriever.index_source(self._SAMPLE_SOURCE)
        matches = retriever.search("greet")
        assert len(matches) >= 1

    def test_search_not_found_returns_empty(self) -> None:
        retriever = CodeSearchRetriever()
        retriever.index_source(self._SAMPLE_SOURCE)
        matches = retriever.search("zzz_nonexistent_xyz")
        assert matches == []

    def test_query_with_match(self) -> None:
        retriever = CodeSearchRetriever()
        retriever.index_source(self._SAMPLE_SOURCE)
        ctx = QueryContext()
        result = retriever.query("greet", ctx)
        assert result.confidence > 0
        assert result.content != ""

    def test_query_no_match(self) -> None:
        retriever = CodeSearchRetriever()
        ctx = QueryContext()
        result = retriever.query("nonexistent_xyz", ctx)
        assert result.confidence == 0.0

    def test_validate_returns_valid(self) -> None:
        retriever = CodeSearchRetriever()
        result = retriever.validate()
        assert result.valid is True


# ---------------------------------------------------------------------------
# ComputationalRetriever
# ---------------------------------------------------------------------------


class TestComputationalRetriever:
    def test_query_valid_expression(self) -> None:
        retriever = ComputationalRetriever()
        ctx = QueryContext()
        result = retriever.query("1 + 1", ctx)
        assert result.confidence > 0
        assert "2" in result.content

    def test_query_invalid_expression(self) -> None:
        retriever = ComputationalRetriever()
        ctx = QueryContext()
        result = retriever.query("not_a_valid_math_expr!!!", ctx)
        assert result.confidence == 0.0

    def test_validate_returns_valid(self) -> None:
        retriever = ComputationalRetriever()
        result = retriever.validate()
        assert result.valid is True
