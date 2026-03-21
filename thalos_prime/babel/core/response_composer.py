"""Deterministic response composition from semantic frames.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..linguistic.semantic_frames import SemanticFrame
from .coordinate_system import Coordinate


class DeterministicResponseComposer:
    """Compose responses deterministically from frames and templates."""

    def compose(self, frame: SemanticFrame, template: str, coordinate: Coordinate) -> str:
        variables: Mapping[str, str] = frame.to_variables()
        materialized = template.format(**variables)
        # Append coordinate metadata while preserving terminal punctuation for coherence checks.
        return f"{materialized} [coord={coordinate.digest[:12]}|var={coordinate.variation_index}]."
