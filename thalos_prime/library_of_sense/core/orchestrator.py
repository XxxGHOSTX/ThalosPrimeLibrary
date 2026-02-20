"""Library of Sense - Query Orchestrator.

Coordinates retrieval, synthesis, and reasoning to answer queries
deterministically using registered source and synthesizer components.
"""

from __future__ import annotations

import logging

from thalos_prime.library_of_sense.core.interfaces import (
    KnowledgeSynthesizer,
    QueryContext,
    QueryDomain,
    ReasoningEngine,
    ReasoningResult,
    RetrievalResult,
    RetrievalSource,
    SynthesisResult,
    ValidationResult,
)
from thalos_prime.library_of_sense.core.state_manager import StateManager

logger = logging.getLogger(__name__)


class QueryOrchestrator:
    """Orchestrates multi-source retrieval, synthesis, and reasoning.

    Coordinates registered RetrievalSource, KnowledgeSynthesizer, and
    ReasoningEngine components to answer queries deterministically.
    """

    def __init__(self, state_manager: StateManager, seed: int = 0) -> None:
        """Initialize the query orchestrator.

        Args:
            state_manager: StateManager instance for tracking operation state.
            seed: Deterministic seed for reproducible query processing.
        """
        self._state_manager = state_manager
        self._seed = seed
        self._sources: list[RetrievalSource] = []
        self._synthesizers: list[KnowledgeSynthesizer] = []
        self._reasoning_engines: dict[QueryDomain, ReasoningEngine] = {}

    def register_source(self, source: RetrievalSource) -> None:
        """Register a retrieval source for use during query processing.

        Args:
            source: RetrievalSource to register.
        """
        self._sources.append(source)

    def register_synthesizer(self, synthesizer: KnowledgeSynthesizer) -> None:
        """Register a knowledge synthesizer.

        Args:
            synthesizer: KnowledgeSynthesizer to register.
        """
        self._synthesizers.append(synthesizer)

    def register_reasoning_engine(
        self,
        domain: QueryDomain,
        engine: ReasoningEngine,
    ) -> None:
        """Register a reasoning engine for a specific domain.

        Args:
            domain: QueryDomain this engine handles.
            engine: ReasoningEngine to register.
        """
        self._reasoning_engines[domain] = engine

    def validate_sources(self) -> list[ValidationResult]:
        """Validate all registered retrieval sources.

        Returns:
            List of ValidationResult for each registered source.
        """
        return [source.validate() for source in self._sources]

    def retrieve(
        self,
        query: str,
        context: QueryContext,
    ) -> list[RetrievalResult]:
        """Retrieve results from all registered sources.

        Args:
            query: The query string to retrieve information for.
            context: Query context with domain and options.

        Returns:
            List of RetrievalResult from all sources.
        """
        results: list[RetrievalResult] = []
        for source in self._sources:
            result = source.query(query, context)
            results.append(result)
            self._state_manager.increment_retrieval_count()
        return results

    def synthesize(
        self,
        results: list[RetrievalResult],
        context: QueryContext,
    ) -> SynthesisResult:
        """Synthesize knowledge from retrieval results using registered synthesizers.

        Args:
            results: List of retrieval results to synthesize.
            context: Query context guiding synthesis.

        Returns:
            SynthesisResult with the best synthesized answer.
        """
        if not self._synthesizers:
            answer = " ".join(r.content for r in results) if results else ""
            return SynthesisResult(answer=answer, confidence=0.5, sources=results)

        synthesis_results = [s.synthesize(results, context) for s in self._synthesizers]
        self._state_manager.increment_synthesis_count()
        return max(synthesis_results, key=lambda r: r.confidence)

    def apply_reasoning(
        self,
        synthesis: SynthesisResult,
        context: QueryContext,
    ) -> ReasoningResult | None:
        """Apply domain-specific reasoning to a synthesis result.

        Args:
            synthesis: SynthesisResult to reason about.
            context: Query context specifying the domain.

        Returns:
            ReasoningResult if a reasoning engine is registered for the domain, else None.
        """
        engine = self._reasoning_engines.get(context.domain)
        if engine is None:
            return None
        return engine.reason(synthesis.answer, context)

    def process_query(self, query: str, context: QueryContext) -> SynthesisResult:
        """Process a complete query through retrieval, synthesis, and reasoning.

        Args:
            query: The query string to process.
            context: Query context with domain and execution options.

        Returns:
            SynthesisResult containing the final answer.
        """
        self._state_manager.increment_query_count()
        logger.info(
            "Processing query: domain=%s seed=%d",
            context.domain.value,
            self._seed,
        )
        results = self.retrieve(query, context)
        synthesis = self.synthesize(results, context)

        if context.require_proof:
            reasoning = self.apply_reasoning(synthesis, context)
            if reasoning is not None:
                synthesis.reasoning_steps.extend(reasoning.proof_steps)
                synthesis.verified = reasoning.valid

        return synthesis


__all__ = ["QueryOrchestrator"]
