"""
Deterministic response composition from semantic frames.
"""

from __future__ import annotations

from typing import Mapping

from .coordinate_system import Coordinate
from ..linguistic.semantic_frames import SemanticFrame


class DeterministicResponseComposer:
    """Compose responses deterministically from frames and templates."""

    def compose(self, frame: SemanticFrame, template: str, coordinate: Coordinate) -> str:
        variables: Mapping[str, str] = frame.to_variables()
        materialized = template.format(**variables)
        # Append coordinate metadata while preserving terminal punctuation for coherence checks.
        return f"{materialized} [coord={coordinate.digest[:12]}|var={coordinate.variation_index}]."
