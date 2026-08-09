"""Deterministic natural-language constraint navigator."""

from __future__ import annotations

import re

MAX_PEPTIDE_LENGTH = 30


def translate_constraints(text: str) -> dict[str, object] | None:
    """Translate lightweight peptide constraints from natural language."""
    if not text:
        return None

    lower = text.lower()
    if "peptide" in lower or "amino" in lower:
        length_match = re.search(r"(\d+)\s*(aa|amino|residue|residues)?", lower)
        length = int(length_match.group(1)) if length_match else 10
        return {
            "domain": "peptide",
            "length": max(1, min(length, MAX_PEPTIDE_LENGTH)),
            "raw": text,
        }
    return None
