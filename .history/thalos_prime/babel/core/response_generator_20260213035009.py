"""
Deterministic response generation pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .coordinate_system import Coordinate
from .semantic_preserving_composer import SemanticPreservingComposer
from ..linguistic.semantic_frames import FrameConstructor, SemanticFrame
from ..linguistic.response_corpus import ResponseCorpus
from ..linguistic.coherence_validator import LinguisticCoherenceValidator, CoherenceReport


@dataclass(frozen=True)
class GeneratedResponse:
    """Container for generated response with metadata."""

    text: str
    coordinate: Coordinate
    template_used: str
    frame: SemanticFrame
    variation_degree: int
    semantic_preserved: bool
    coherence_report: CoherenceReport

    @property
    def semantic_core(self):  # type: ignore[override]
        return self.frame.semantic_core


class ResponseGenerator:
    """Deterministic generator that maps input to responses."""

    def __init__(
        self,
        composer: SemanticPreservingComposer,
        frame_constructor: FrameConstructor,
        corpus: ResponseCorpus,
        coherence_validator: LinguisticCoherenceValidator,
    ) -> None:
        self.composer = composer
        self.frame_constructor = frame_constructor
        self.corpus = corpus
        self.coherence_validator = coherence_validator

    def generate(self, user_input: str, coordinate: Coordinate, variation_degree: int) -> GeneratedResponse:
        frame = self.frame_constructor.construct(user_input)
        templates: List[str] = self.corpus.get_templates_for_frame(frame.frame_type)
        if not templates:
            raise ValueError(f"No templates available for frame {frame.frame_type}")
        template_index = coordinate.variation_index % len(templates)
        template = templates[template_index]
        text, preserved = self.composer.compose_with_validation(frame, template, coordinate)
        coherence_report = self.coherence_validator.validate(text)
        return GeneratedResponse(
            text=text,
            coordinate=coordinate,
            template_used=template,
            frame=frame,
            variation_degree=variation_degree,
            semantic_preserved=preserved,
            coherence_report=coherence_report,
        )
