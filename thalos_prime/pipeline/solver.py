"""Deterministic candidate constraint solver stage."""

from __future__ import annotations

from typing import Any

try:
    from z3 import Bool as _Z3Bool
    from z3 import Solver as _Z3Solver
    from z3 import sat as _z3_sat
except ImportError:  # pragma: no cover - optional dependency path
    _Z3Bool = None
    _Z3Solver = None
    _z3_sat = None


def _as_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _z3_constraint_score(constraints: dict[str, object]) -> float | None:
    """Return constraint score using z3 when available."""
    if _Z3Bool is None or _Z3Solver is None or _z3_sat is None:
        return None

    hard = _as_string_list(constraints.get("hard", []))
    solver = _Z3Solver()
    flags = [_Z3Bool(f"c{i}") for i, _ in enumerate(hard)]
    for flag in flags:
        solver.add(flag)

    if solver.check() == _z3_sat:
        return 100.0 if hard else 90.0
    return 0.0


def validate_candidates(
    candidates: list[dict[str, object]],
    *,
    constraints: dict[str, object],
) -> list[dict[str, object]]:
    """Validate candidates against hard constraints deterministically."""
    z3_score = _z3_constraint_score(constraints)
    validated: list[dict[str, object]] = []
    hard_constraints = _as_string_list(constraints.get("hard", []))

    for candidate in candidates:
        text = str(candidate["text"])
        satisfied = True
        penalty = 0.0

        for hard in hard_constraints:
            if hard == "deterministic=true":
                continue
            if hard == "intent=search":
                continue
            if hard.startswith("max_results<="):
                continue
            if hard not in text:
                satisfied = False
                penalty += 15.0

        constraint_score = z3_score if z3_score is not None else max(0.0, 100.0 - penalty)
        enriched: dict[str, Any] = {
            **candidate,
            "constraint_score": float(constraint_score),
            "constraints_satisfied": satisfied,
        }
        if not satisfied:
            enriched["constraint_score"] = max(0.0, float(constraint_score) - penalty)
        validated.append(enriched)

    return validated
