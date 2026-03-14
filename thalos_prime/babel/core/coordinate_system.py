"""Deterministic coordinate mathematics for Babel responses.

Provides :class:`Coordinate`, :class:`CoordinateValidator`, and
:class:`DeterministicCoordinateDeriver` for address generation and validation.

Data Plane: coordinate mathematics only; no lifecycle coordination logic.
"""

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
        """Return the canonical coordinate string."""
        return self.as_string()


class CoordinateValidator:
    """Validate coordinate integrity and structure.

    Implements the six-method lifecycle contract so that it may participate
    in lifecycle-managed subsystems.
    """

    MIN_DIGEST_LENGTH: Final[int] = 16

    def initialize(self) -> None:
        """No-op initializer; CoordinateValidator is stateless."""

    def operate(self) -> None:
        """No-op operate; CoordinateValidator has no background work."""

    def reconcile(self) -> None:
        """No-op reconcile; CoordinateValidator holds no mutable state."""

    def checkpoint(self) -> dict[str, object]:
        """Return an empty checkpoint; CoordinateValidator is stateless.

        Returns:
            Dict identifying the component.

        """
        return {"component": "CoordinateValidator"}

    def terminate(self) -> None:
        """No-op terminate; CoordinateValidator holds no resources."""

    @classmethod
    def validate(cls, coordinate: Coordinate) -> bool:
        """Return True when *coordinate* is structurally valid.

        Args:
            coordinate: Coordinate instance to check.

        Returns:
            True if digest length, character set, and variation index are valid.

        """
        digest = coordinate.digest
        if len(digest) < cls.MIN_DIGEST_LENGTH:
            return False
        if not all(c in "0123456789abcdef" for c in digest):
            return False
        return coordinate.variation_index >= 0


class DeterministicCoordinateDeriver:
    """Derive deterministic coordinates from input context."""

    def __init__(self, seed: str) -> None:
        """Initialize with *seed*.

        Args:
            seed: Deterministic seed string for coordinate derivation.

        """
        self.seed: Final[str] = seed

    def derive(self, text: str, context: VariationalContext) -> Coordinate:
        """Compute coordinate deterministically from text and context.

        Args:
            text: Input text to derive a coordinate from.
            context: Variational context providing turn and variation indices.

        Returns:
            Deterministic :class:`Coordinate` for the given inputs.

        Raises:
            ValueError: When the derived coordinate fails structural validation.

        """
        normalized = ContextHasher.normalize_text(text)
        digest_source = f"{self.seed}|{normalized}|{context.turn_index}|{context.variation_index}"
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
