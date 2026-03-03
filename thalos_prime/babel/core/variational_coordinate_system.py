"""Variation-aware coordinate derivation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .context_hasher import ContextHasher


@dataclass(frozen=True)
class VariationalContext:
    """Deterministic context inputs for a single turn."""

    session_id: str
    turn_index: int
    variation_index: int


class VariationalCoordinateDeriver:
    """Derive variation-aware coordinates."""

    def __init__(self, base_seed: str) -> None:
        """Initialize with base seed."""
        self.base_seed: Final[str] = base_seed

    def variation_seed(self, context: VariationalContext) -> str:
        """Compute deterministic seed for variation."""
        seed_material = f"{self.base_seed}|{context.turn_index}|{context.variation_index}"
        return ContextHasher.hash_text(seed_material)[:16]
