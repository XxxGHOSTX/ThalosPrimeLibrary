"""
Semantic-preserving response composition.
"""

from __future__ import annotations

from typing import Tuple

from .coordinate_system import Coordinate
from .response_composer import DeterministicResponseComposer
from ..linguistic.semantic_invariants import SemanticInvariantChecker
from ..linguistic.semantic_frames import SemanticFrame


class SemanticPreservingComposer(DeterministicResponseComposer):
    """Compose responses while enforcing semantic invariants."""

    def __init__(self, invariant_checker: SemanticInvariantChecker):
        super().__init__()
        self.invariant_checker = invariant_checker

    def compose_with_validation(self, frame: SemanticFrame, template: str, coordinate: Coordinate) -> Tuple[str, bool]:
        text = self.compose(frame, template, coordinate)
        preserved = self.invariant_checker.validate(frame)
        return text, preserved
