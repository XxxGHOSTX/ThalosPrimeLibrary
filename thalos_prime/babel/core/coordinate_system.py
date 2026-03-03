"""Deterministic coordinate mathematics for Babel responses."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Final

from .context_hasher import ContextHasher

if TYPE_CHECKING:
    from .variational_coordinate_system import VariationalContext


@dataclass(frozen=True)
class Coordinate:
    """Deterministic address for a generated response."""

    seed: str
    digest: str
    variation_index: int

    def as_string(self) -> str:
        """Return canonical coordinate string representation."""
        return f"{self.seed}:{self.digest}:{self.variation_index}"

    def __str__(self) -> str:
        """Return canonical string representation."""
        return self.as_string()


class CoordinateValidator:
    """Validate coordinate integrity and structure."""

    MIN_DIGEST_LENGTH: Final[int] = 16

    @classmethod
    def validate(cls, coordinate: Coordinate) -> bool:
        """Validate coordinate integrity."""
        digest = coordinate.digest
        if len(digest) < cls.MIN_DIGEST_LENGTH:
            return False
        if not all(c in "0123456789abcdef" for c in digest):
            return False
        return coordinate.variation_index >= 0


class DeterministicCoordinateDeriver:
    """Derive deterministic coordinates from input context."""

    def __init__(self, seed: str) -> None:
        """Initialize with seed."""
        self.seed: Final[str] = seed

    def derive(self, text: str, context: VariationalContext) -> Coordinate:
        """Compute coordinate deterministically from text and context."""
        normalized = ContextHasher.normalize_text(text)
        # Derive coordinate deterministically from seed, text, and variation index.
        digest_source = (
            f"{self.seed}|{normalized}|{context.turn_index}|{context.variation_index}"
        )
        digest = sha256(digest_source.encode("utf-8")).hexdigest()
        coordinate = Coordinate(
            seed=self.seed,
            digest=digest[:32],
            variation_index=context.variation_index,
        )
        if not CoordinateValidator.validate(coordinate):
            msg = "Invalid coordinate generated"
            raise ValueError(msg)
        return coordinate
