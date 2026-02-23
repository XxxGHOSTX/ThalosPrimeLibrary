"""Integration tests for the Library of Sense subsystem."""

from __future__ import annotations

from thalos_prime.library_of_sense.api.query_handler import QueryHandler
from thalos_prime.library_of_sense.api.response_builder import ResponseBuilder
from thalos_prime.library_of_sense.core.interfaces import QueryContext, QueryDomain
from thalos_prime.library_of_sense.core.orchestrator import QueryOrchestrator
from thalos_prime.library_of_sense.core.state_manager import StateManager
from thalos_prime.library_of_sense.retrieval.computational import ComputationalRetriever
from thalos_prime.library_of_sense.retrieval.knowledge_graph import (
    GraphTriple,
    KnowledgeGraphRetriever,
)
from thalos_prime.library_of_sense.synthesis.knowledge_fusion import KnowledgeFusion


class TestQueryHandlerLifecycle:
    def test_full_lifecycle_with_kg(self) -> None:
        handler = QueryHandler(seed=42)
        handler.initialize()
        handler.validate()
        handler.operate()

        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        kg.add_triple(GraphTriple(subject="Python", predicate="is", obj="language"))
        handler.register_source(kg)

        fusion = KnowledgeFusion()
        handler.register_synthesizer(fusion)

        ctx = QueryContext(domain=QueryDomain.KNOWLEDGE_GRAPH)
        answer = handler.handle_query("Python", ctx)
        assert answer.query == "Python"
        assert isinstance(answer.answer, str)

        handler.checkpoint()
        handler.terminate()

    def test_full_lifecycle_empty_sources(self) -> None:
        handler = QueryHandler(seed=0)
        handler.initialize()
        handler.validate()
        handler.operate()
        ctx = QueryContext()
        answer = handler.handle_query("test query", ctx)
        assert answer.query == "test query"
        handler.terminate()

    def test_reconcile_then_operate(self) -> None:
        handler = QueryHandler(seed=1)
        handler.initialize()
        handler.validate()
        handler.reconcile()
        handler.operate()
        handler.terminate()

    def test_handle_raw_returns_synthesis_result(self) -> None:
        handler = QueryHandler(seed=0)
        handler.initialize()
        handler.validate()
        result = handler.handle_raw("test")
        assert hasattr(result, "answer")
        handler.terminate()


class TestComputationalIntegration:
    def test_computational_query_through_orchestrator(self) -> None:
        sm = StateManager(seed=0)
        sm.initialize()
        sm.validate()
        orchestrator = QueryOrchestrator(sm, seed=0)

        comp = ComputationalRetriever()
        orchestrator.register_source(comp)

        fusion = KnowledgeFusion()
        orchestrator.register_synthesizer(fusion)

        ctx = QueryContext(domain=QueryDomain.COMPUTATIONAL)
        result = orchestrator.process_query("2 + 2", ctx)
        assert isinstance(result.answer, str)
        sm.terminate()


class TestResponseBuilder:
    def test_build_response_from_handler(self) -> None:
        handler = QueryHandler(seed=0)
        handler.initialize()
        handler.validate()

        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        kg.add_triple(GraphTriple(subject="test", predicate="is", obj="valid"))
        handler.register_source(kg)

        ctx = QueryContext()
        answer = handler.handle_query("test", ctx)
        builder = ResponseBuilder()
        response = builder.build(answer)

        assert "schema_version" in response
        assert response["query"] == "test"
        handler.terminate()

    def test_build_error_response(self) -> None:
        builder = ResponseBuilder()
        response = builder.build_error("my_query", "Something went wrong")
        assert response["query"] == "my_query"
        assert "error" in response


class TestMultiSourceOrchestration:
    def test_multiple_sources_merged(self) -> None:
        sm = StateManager(seed=0)
        sm.initialize()
        sm.validate()
        orchestrator = QueryOrchestrator(sm, seed=0)

        kg = KnowledgeGraphRetriever()
        kg.initialize()
        kg.validate()
        kg.operate()
        kg.add_triple(GraphTriple(subject="AI", predicate="is", obj="technology"))
        comp = ComputationalRetriever()

        orchestrator.register_source(kg)
        orchestrator.register_source(comp)
        orchestrator.register_synthesizer(KnowledgeFusion())

        ctx = QueryContext()
        result = orchestrator.process_query("AI", ctx)
        assert isinstance(result.answer, str)
        sm.terminate()
