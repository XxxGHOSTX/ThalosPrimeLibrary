"""Deterministic semantic decomposition helpers."""

from __future__ import annotations


def semantic_deconstruct(text: str) -> dict[str, object]:
    """Classify prompt across deterministic semantic nodes."""
    if not text:
        return {"fragments": [], "dimensions": {}, "node": "unknown"}

    lower = text.lower()
    fragments = [fragment for fragment in text.split() if fragment]

    node = "narrative"
    if any(tok in lower for tok in ["dna", "rna", "gene", "peptide", "protein", "sequence"]):
        node = "genomic"
    elif any(tok in lower for tok in ["proof", "theorem", "math", "logical", "axiom", "compute"]):
        node = "logical"
    elif any(tok in lower for tok in ["molecule", "compound", "chem", "synthesis", "reaction"]):
        node = "chemical"

    dimensions = {
        "physical": f"[physical/chemical] Nexus view for: {lower[:200]}",
        "logical": f"[logical/mathematical] Nexus view for: {lower[:200]}",
        "narrative": f"[linguistic/narrative] Nexus view for: {lower[:200]}",
    }
    return {"fragments": fragments, "dimensions": dimensions, "node": node}
