"""Semantic-preserving response composition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .response_composer import DeterministicResponseComposer

if TYPE_CHECKING:
    from thalos_prime.babel.linguistic.semantic_frames import SemanticFrame
    from thalos_prime.babel.linguistic.semantic_invariants import SemanticInvariantChecker

    from .coordinate_system import Coordinate


class SemanticPreservingComposer(DeterministicResponseComposer):
    """Compose responses while enforcing semantic invariants."""

    def __init__(self, invariant_checker: SemanticInvariantChecker) -> None:
        """Initialise the composer with an invariant checker."""
        super().__init__()
        self.invariant_checker = invariant_checker

    def compose_with_validation(
        self, frame: SemanticFrame, template: str, coordinate: Coordinate
    ) -> tuple[str, bool]:
        """Compose a response and validate semantic invariants.

        Returns text and a preservation flag.
        """
        text = self.compose(frame, template, coordinate)
        preserved = self.invariant_checker.validate(frame)
        return text, preserved
