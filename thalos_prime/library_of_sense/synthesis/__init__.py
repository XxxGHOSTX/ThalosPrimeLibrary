"""Library of Sense - Synthesis components for knowledge fusion and answer generation."""

from thalos_prime.library_of_sense.synthesis.knowledge_fusion import KnowledgeFusion
from thalos_prime.library_of_sense.synthesis.conflict_resolution import ConflictResolver
from thalos_prime.library_of_sense.synthesis.verification import ResultVerifier
from thalos_prime.library_of_sense.synthesis.answer_generator import (
    AnswerGenerator,
    StructuredAnswer,
)

__all__ = [
    "KnowledgeFusion",
    "ConflictResolver",
    "ResultVerifier",
    "AnswerGenerator",
    "StructuredAnswer",
]
