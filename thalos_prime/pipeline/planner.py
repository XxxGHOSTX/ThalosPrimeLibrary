"""Deterministic execution planner stage."""

from __future__ import annotations


def build_plan(
    *,
    selected_candidate: dict[str, object],
    intent: dict[str, str],
    constraints: dict[str, object],
) -> list[dict[str, object]]:
    """Build a deterministic execution plan for the selected candidate."""
    return [
        {
            "step": 1,
            "action": "confirm_intent",
            "intent": intent["label"],
        },
        {
            "step": 2,
            "action": "apply_constraints",
            "hard_constraints": list(constraints.get("hard", [])),
        },
        {
            "step": 3,
            "action": "execute_selected_candidate",
            "candidate_id": str(selected_candidate["candidate_id"]),
            "address": str(selected_candidate["address"]),
        },
    ]
