"""
Deterministic search engine mapping coordinates to responses.
"""

from __future__ import annotations

from typing import Dict

from .coordinate_system import Coordinate


class DeterministicSearchEngine:
    """Simple in-memory search keyed by coordinates."""

    def __init__(self) -> None:
        self._index: Dict[str, str] = {}

    def record(self, coordinate: Coordinate, text: str) -> None:
        self._index[coordinate.as_string()] = text

    def retrieve(self, coordinate: Coordinate) -> str | None:
        return self._index.get(coordinate.as_string())
