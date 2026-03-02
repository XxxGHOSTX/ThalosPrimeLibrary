"""
Semantic orchestrator for Babel subsystem.
"""

from __future__ import annotations

from pathlib import Path

from ..core.coordinate_system import DeterministicCoordinateDeriver
from ..core.response_generator import ResponseGenerator, GeneratedResponse
from ..core.semantic_preserving_composer import SemanticPreservingComposer
from ..core.variational_coordinate_system import VariationalCoordinateDeriver, VariationalContext
from ..core.search_engine import DeterministicSearchEngine
from ..linguistic.intent_classifier import DeterministicIntentClassifier
from ..linguistic.semantic_frames import FrameConstructor
from ..linguistic.semantic_invariants import SemanticInvariantChecker
from ..linguistic.response_corpus import ResponseCorpus
from ..linguistic.coherence_validator import LinguisticCoherenceValidator
from .orchestrator import ThalobalOrchestrator


class SemanticOrchestrator(ThalobalOrchestrator):
    """Full semantic orchestrator with deterministic variation."""

    def __init__(self, storage_path: Path, seed: str = "thalos-babel-seed") -> None:
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
        turn_index = self.state_manager.next_turn_index(session_id, self.state)
        variation_index = turn_index
        context = VariationalContext(
            session_id=session_id,
            turn_index=turn_index,
            variation_index=variation_index,
        )
        coordinate = self.coordinate_deriver.derive(user_input, context)
        variation_degree = variation_index
        response = self.response_generator.generate(
            user_input=user_input,
            coordinate=coordinate,
            variation_degree=variation_degree,
        )
        self.search_engine.record(coordinate, response.text)
        self._record_state(coordinate.as_string())
        return response
