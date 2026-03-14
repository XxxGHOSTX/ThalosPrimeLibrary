"""Deterministic search engine mapping coordinates to responses."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .coordinate_system import Coordinate


class DeterministicSearchEngine:
    """Simple in-memory search keyed by coordinates."""

    def __init__(self) -> None:
        """Initialise an empty in-memory search index."""
        self._index: dict[str, str] = {}

    def record(self, coordinate: Coordinate, text: str) -> None:
        """Index *text* under *coordinate*."""
        self._index[coordinate.as_string()] = text

    def retrieve(self, coordinate: Coordinate) -> str | None:
        """Return text for *coordinate*, or ``None`` if not indexed."""
        return self._index.get(coordinate.as_string())
