"""Consistency reconciliation for Babel subsystem."""

from __future__ import annotations

from dataclasses import dataclass

from thalos_prime.babel.core.coordinate_system import Coordinate, CoordinateValidator


@dataclass(frozen=True)
class Inconsistency:
    """Immutable record of a detected state inconsistency."""

    component: str
    description: str
    severity: str


class Reconciler:
    """Detect and resolve inconsistencies."""

    def check_state(self, state_last_coordinate: str | None) -> list[Inconsistency]:
        """Validate last_coordinate format and return detected inconsistencies."""
        issues: list[Inconsistency] = []
        if state_last_coordinate:
            try:
                seed, digest, var_str = state_last_coordinate.split(":")
                coord = Coordinate(seed=seed, digest=digest, variation_index=int(var_str))
                if not CoordinateValidator.validate(coord):
                    issues.append(Inconsistency("state", "Invalid coordinate format", "critical"))
            except (ValueError, AttributeError, IndexError):
                issues.append(Inconsistency("state", "Malformed coordinate string", "critical"))
        return issues

    def resolve(self, inconsistencies: list[Inconsistency]) -> None:
        """Raise RuntimeError if any critical inconsistencies are present."""
        critical = [i for i in inconsistencies if i.severity == "critical"]
        if critical:
            descriptions = ", ".join(i.description for i in critical)
            msg = f"Critical inconsistencies detected: {descriptions}"
            raise RuntimeError(msg)
