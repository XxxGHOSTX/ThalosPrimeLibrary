"""Library of Sense - Query Handler.

Processes incoming query requests through the full Library of Sense pipeline:
retrieval, synthesis, reasoning, and answer generation. Implements all
required lifecycle methods for deterministic operation.
"""

from __future__ import annotations

import logging
from typing import Final

from thalos_prime.library_of_sense.core.interfaces import (
    KnowledgeSynthesizer,
    QueryContext,
    QueryDomain,
    ReasoningEngine,
    RetrievalSource,
    SynthesisResult,
)
from thalos_prime.library_of_sense.core.lifecycle import LifecycleState, SubsystemLifecycle
from thalos_prime.library_of_sense.core.orchestrator import QueryOrchestrator
from thalos_prime.library_of_sense.core.state_manager import StateManager
from thalos_prime.library_of_sense.synthesis.answer_generator import (
    AnswerGenerator,
    StructuredAnswer,
)
from thalos_prime.library_of_sense.synthesis.verification import ResultVerifier

logger = logging.getLogger(__name__)

_SUBSYSTEM_NAME: Final[str] = "library_of_sense.query_handler"


class QueryHandler:
    """Handles incoming query requests through the full Library of Sense pipeline.

    Orchestrates retrieval, synthesis, verification, and answer generation
    with complete lifecycle management for deterministic, reproducible operation.
    """

    def __init__(self, seed: int = 0) -> None:
        """Initialize the query handler.

        Args:
            seed: Deterministic seed for replay identification.

        """
        self._seed = seed
        self._state_manager = StateManager(seed=seed)
        self._orchestrator = QueryOrchestrator(self._state_manager, seed=seed)
        self._verifier = ResultVerifier()
        self._answer_generator = AnswerGenerator()
        self._lifecycle = SubsystemLifecycle(_SUBSYSTEM_NAME, seed=seed)

    def initialize(self) -> None:
        """Initialize all sub-components and transition to INITIALIZED state."""
        self._lifecycle.transition(LifecycleState.INITIALIZING, "Initializing sub-components")
        self._state_manager.initialize()
        self._lifecycle.transition(LifecycleState.INITIALIZED, "Initialization complete")
        logger.info("QueryHandler initialized with seed=%d", self._seed)

    def validate(self) -> None:
        """Validate handler configuration and transition to READY state.

        Raises:
            RuntimeError: If state manager validation fails.

        """
        self._lifecycle.transition(LifecycleState.VALIDATING, "Validating configuration")
        self._state_manager.validate()
        self._lifecycle.transition(LifecycleState.READY, "Validation passed")
        logger.info("QueryHandler validation passed")

    def operate(self) -> None:
        """Transition to OPERATING state for active query processing."""
        self._lifecycle.transition(LifecycleState.OPERATING, "Entering operation mode")
        self._state_manager.operate()
        logger.info("QueryHandler operating")

    def reconcile(self) -> None:
        """Reconcile internal state and return to READY state."""
        self._lifecycle.transition(LifecycleState.RECONCILING, "Reconciling state")
        self._state_manager.reconcile()
        self._lifecycle.transition(LifecycleState.READY, "Reconciliation complete")
        logger.info("QueryHandler reconciliation complete")

    def checkpoint(self) -> None:
        """Emit structured checkpoint log for current handler state."""
        self._lifecycle.transition(LifecycleState.CHECKPOINTING, "Creating checkpoint")
        self._state_manager.checkpoint()
        logger.info(
            "QueryHandler checkpoint: seed=%d state=%s",
            self._seed,
            self._lifecycle.state.value,
        )
        self._lifecycle.transition(LifecycleState.READY, "Checkpoint complete")

    def terminate(self) -> None:
        """Terminate the handler and all sub-components."""
        self._lifecycle.transition(LifecycleState.TERMINATING, "Terminating")
        self._state_manager.terminate()
        self._lifecycle.transition(LifecycleState.TERMINATED, "Terminated")
        logger.info("QueryHandler terminated")

    def register_source(self, source: RetrievalSource) -> None:
        """Register a retrieval source with the orchestrator.

        Args:
            source: RetrievalSource to register.

        """
        self._orchestrator.register_source(source)
        if hasattr(source, "__class__"):
            self._state_manager.add_source(source.__class__.__name__)

    def register_synthesizer(self, synthesizer: KnowledgeSynthesizer) -> None:
        """Register a knowledge synthesizer with the orchestrator.

        Args:
            synthesizer: KnowledgeSynthesizer to register.

        """
        self._orchestrator.register_synthesizer(synthesizer)

    def register_reasoning_engine(
        self, domain: QueryDomain, engine: ReasoningEngine
    ) -> None:
        """Register a reasoning engine for a specific domain.

        Args:
            domain: QueryDomain this engine handles.
            engine: ReasoningEngine to register.

        """
        self._orchestrator.register_reasoning_engine(domain, engine)

    def handle_query(
        self,
        query: str,
        context: QueryContext | None = None,
    ) -> StructuredAnswer:
        """Process a query through the full Library of Sense pipeline.

        Args:
            query: The query string to process.
            context: Optional QueryContext; defaults to GENERAL domain.

        Returns:
            StructuredAnswer with the generated answer and provenance.

        """
        if context is None:
            context = QueryContext(seed=self._seed)

        synthesis = self._orchestrator.process_query(query, context)
        synthesis = self._verifier.verify_and_mark(synthesis)
        return self._answer_generator.generate(query, synthesis, context)

    def handle_raw(
        self,
        query: str,
        context: QueryContext | None = None,
    ) -> SynthesisResult:
        """Process a query and return the raw SynthesisResult without formatting.

        Args:
            query: The query string to process.
            context: Optional QueryContext; defaults to GENERAL domain.

        Returns:
            SynthesisResult with the answer and source provenance.

        """
        if context is None:
            context = QueryContext(seed=self._seed)
        return self._orchestrator.process_query(query, context)


__all__ = ["QueryHandler"]
