"""Deterministic search engine mapping coordinates to responses."""

from __future__ import annotations

from .coordinate_system import Coordinate


class DeterministicSearchEngine:
    """Simple in-memory search keyed by coordinates."""

    def __init__(self) -> None:
        """Initialize an empty in-memory coordinate index."""
        self._index: dict[str, str] = {}

    def record(self, coordinate: Coordinate, text: str) -> None:
        """Store *text* keyed by *coordinate*."""
        self._index[coordinate.as_string()] = text

    def retrieve(self, coordinate: Coordinate) -> str | None:
        """Return text for *coordinate*, or None if not found."""
        return self._index.get(coordinate.as_string())
