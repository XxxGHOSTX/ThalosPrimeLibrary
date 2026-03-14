"""Semantic orchestrator for Babel subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING

from thalos_prime.babel.core.coordinate_system import DeterministicCoordinateDeriver
from thalos_prime.babel.core.response_generator import GeneratedResponse, ResponseGenerator
from thalos_prime.babel.core.search_engine import DeterministicSearchEngine
from thalos_prime.babel.core.semantic_preserving_composer import SemanticPreservingComposer
from thalos_prime.babel.core.variational_coordinate_system import (
    VariationalContext,
    VariationalCoordinateDeriver,
)
from thalos_prime.babel.linguistic.coherence_validator import LinguisticCoherenceValidator
from thalos_prime.babel.linguistic.intent_classifier import DeterministicIntentClassifier
from thalos_prime.babel.linguistic.response_corpus import ResponseCorpus
from thalos_prime.babel.linguistic.semantic_frames import FrameConstructor
from thalos_prime.babel.linguistic.semantic_invariants import SemanticInvariantChecker

from .orchestrator import ThalobalOrchestrator

if TYPE_CHECKING:
    from pathlib import Path


class SemanticOrchestrator(ThalobalOrchestrator):
    """Full semantic orchestrator with deterministic variation."""

    def __init__(self, storage_path: Path, seed: str = "thalos-babel-seed") -> None:
        """Initialise the semantic orchestrator with all linguistic sub-components."""
        super().__init__(storage_path, seed)
        self.coordinate_deriver = DeterministicCoordinateDeriver(seed)
        self.variation_deriver = VariationalCoordinateDeriver(seed)
        self.intent_classifier = DeterministicIntentClassifier()
        self.frame_constructor = FrameConstructor(self.intent_classifier)
        self.invariant_checker = SemanticInvariantChecker()
        self.corpus = ResponseCorpus()
        self.coherence_validator = LinguisticCoherenceValidator()
        self.composer = SemanticPreservingComposer(self.invariant_checker)
        self.response_generator = ResponseGenerator(
            composer=self.composer,
            frame_constructor=self.frame_constructor,
            corpus=self.corpus,
            coherence_validator=self.coherence_validator,
        )
        self.search_engine = DeterministicSearchEngine()

    def handle_semantic_input(self, user_input: str, session_id: str) -> GeneratedResponse:
        """Process user input and return a deterministically generated response."""
        turn_index = self.state_manager.next_turn_index(session_id, self.state)
        variation_index = turn_index
        context = VariationalContext(
            session_id=session_id,
            turn_index=turn_index,
            variation_index=variation_index,
        )
        coordinate = self.coordinate_deriver.derive(user_input, context)
        variation_seed = self.variation_deriver.variation_seed(context)
        variation_degree = int(variation_seed, 16) % 5
        response = self.response_generator.generate(
            user_input=user_input,
            coordinate=coordinate,
            variation_degree=variation_degree,
        )
        self.search_engine.record(coordinate, response.text)
        self._record_state(coordinate.as_string())
        return response
