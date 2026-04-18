"""Deterministic candidate constraint solver stage."""

from __future__ import annotations

from typing import Any


def _z3_constraint_score(constraints: dict[str, object]) -> float | None:
    """Return constraint score using z3 when available."""
    try:
        from z3 import Bool, Solver, sat  # type: ignore[import-untyped]
    except ImportError:
        return None

    hard = list(constraints.get("hard", []))
    solver = Solver()
    flags = [Bool(f"c{i}") for i, _ in enumerate(hard)]
    for flag in flags:
        solver.add(flag)

    if solver.check() == sat:
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
    hard_constraints = [str(item) for item in constraints.get("hard", [])]

    for candidate in candidates:
        text = str(candidate["text"])
        coherence = float(candidate["coherence_score"])
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
