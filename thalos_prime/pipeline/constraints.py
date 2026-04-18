"""Deterministic constraints derivation stage."""

from __future__ import annotations

import re


def derive_constraints(input_text: str, *, intent: dict[str, str]) -> dict[str, object]:
    """Derive hard/soft constraints and assumptions from user input."""
    lowered = input_text.lower()
    hard_constraints: list[str] = []
    soft_constraints: list[str] = []
    assumptions: list[str] = []

    max_match = re.search(r"max(?:imum)?\s+(\d+)", lowered)
    if max_match is not None:
        hard_constraints.append(f"max_results<={int(max_match.group(1))}")

    if "deterministic" in lowered:
        hard_constraints.append("deterministic=true")
    else:
        assumptions.append("deterministic=true")

    if intent["label"] == "search":
        hard_constraints.append("intent=search")
    elif intent["label"] == "design":
        soft_constraints.append("prefer_novelty")
    else:
        soft_constraints.append("prefer_clarity")

    return {
        "hard": hard_constraints,
        "soft": soft_constraints,
        "assumptions": assumptions,
    }
