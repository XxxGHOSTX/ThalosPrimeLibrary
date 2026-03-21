"""Deterministic response composition from semantic frames."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from thalos_prime.babel.linguistic.semantic_frames import SemanticFrame

    from .coordinate_system import Coordinate


class DeterministicResponseComposer:
    """Compose responses deterministically from frames and templates."""

    def compose(self, frame: SemanticFrame, template: str, coordinate: Coordinate) -> str:
        """Materialize *template* with *frame* variables and append coordinate metadata."""
        variables: Mapping[str, str] = frame.to_variables()
        materialized = template.format(**variables)
        # Append coordinate metadata while preserving terminal punctuation for coherence checks.
        return f"{materialized} [coord={coordinate.digest[:12]}|var={coordinate.variation_index}]."
