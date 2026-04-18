"""Deterministic intent extraction stage."""

from __future__ import annotations

_DEF_TOKENS = ("define", "what is", "meaning", "explain")
_SEARCH_TOKENS = ("search", "find", "lookup", "discover")
_DESIGN_TOKENS = ("design", "invent", "build", "plan")


def extract_intent(input_text: str, *, intent_override: str | None = None) -> dict[str, str]:
    """Extract a deterministic intent profile from input text."""
    normalized = " ".join(input_text.strip().split())
    lowered = normalized.lower()

    if intent_override:
        intent = intent_override.lower()
    elif any(token in lowered for token in _SEARCH_TOKENS):
        intent = "search"
    elif any(token in lowered for token in _DEF_TOKENS):
        intent = "explain"
    elif any(token in lowered for token in _DESIGN_TOKENS):
        intent = "design"
    else:
        intent = "chat"

    return {
        "label": intent,
        "normalized_input": normalized,
        "query_terms": " ".join(sorted(set(lowered.split()))),
    }
