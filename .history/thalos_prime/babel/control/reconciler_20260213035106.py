"""
Consistency reconciliation for Babel subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..core.coordinate_system import CoordinateValidator, Coordinate


@dataclass(frozen=True)
class Inconsistency:
    component: str
    description: str
    severity: str


class Reconciler:
    """Detect and resolve inconsistencies."""

    def check_state(self, state_last_coordinate: str | None) -> List[Inconsistency]:
        issues: List[Inconsistency] = []
        if state_last_coordinate:
            try:
                seed, digest, var_str = state_last_coordinate.split(":")
                coord = Coordinate(seed=seed, digest=digest, variation_index=int(var_str))
                if not CoordinateValidator.validate(coord):
                    issues.append(Inconsistency("state", "Invalid coordinate format", "critical"))
            except Exception:
                issues.append(Inconsistency("state", "Malformed coordinate string", "critical"))
        return issues

    def resolve(self, inconsistencies: List[Inconsistency]) -> None:
        critical = [i for i in inconsistencies if i.severity == "critical"]
        if critical:
            descriptions = ", ".join(i.description for i in critical)
            raise RuntimeError(f"Critical inconsistencies detected: {descriptions}")
