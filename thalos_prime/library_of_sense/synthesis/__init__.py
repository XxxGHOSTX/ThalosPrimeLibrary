"""Library of Sense - Synthesis components for knowledge fusion and answer generation."""

from thalos_prime.library_of_sense.synthesis.answer_generator import (
    AnswerGenerator,
    StructuredAnswer,
)
from thalos_prime.library_of_sense.synthesis.conflict_resolution import ConflictResolver
from thalos_prime.library_of_sense.synthesis.knowledge_fusion import KnowledgeFusion
from thalos_prime.library_of_sense.synthesis.verification import ResultVerifier

__all__ = [
    "AnswerGenerator",
    "ConflictResolver",
    "KnowledgeFusion",
    "ResultVerifier",
    "StructuredAnswer",
]
