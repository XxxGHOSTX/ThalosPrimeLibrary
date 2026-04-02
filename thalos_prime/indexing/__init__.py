"""Thalos Prime - PRP-based Indexing subsystem.

Provides deterministic content-to-coordinate mapping using an AES-128-ECB
based keyed PRP. Coordinates are 5-tuples (hexagon, wall, shelf, volume, page)
derived deterministically from content hashes.
"""

from thalos_prime.indexing.prp import (
    ArtifactCoordinates,
    Coordinate,
    CoordinateType,
    PrpIndexer,
)

__all__ = [
    "ArtifactCoordinates",
    "Coordinate",
    "CoordinateType",
    "PrpIndexer",
]
