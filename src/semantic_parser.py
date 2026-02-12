from typing import Dict, List


def semantic_deconstruct(text: str) -> Dict:
    """
    Lightweight semantic decomposition that classifies the prompt across
    multiple modalities and emits a structured "nexus" payload.
    """
    if not text:
        return {"fragments": [], "dimensions": {}, "node": "unknown"}

    lower = text.lower()
    fragments: List[str] = [frag for frag in text.split() if frag]

    node = "narrative"
    if any(tok in lower for tok in ["dna", "rna", "gene", "peptide", "protein", "sequence"]):
        node = "genomic"
    elif any(tok in lower for tok in ["proof", "theorem", "math", "logical", "axiom", "compute"]):
        node = "logical"
    elif any(tok in lower for tok in ["molecule", "compound", "chem", "synthesis", "reaction"]):
        node = "chemical"

    dimensions = {
        "physical": _dimension_text("physical/chemical", lower),
        "logical": _dimension_text("logical/mathematical", lower),
        "narrative": _dimension_text("linguistic/narrative", lower),
    }

    return {"fragments": fragments, "dimensions": dimensions, "node": node}


def _dimension_text(label: str, text: str) -> str:
    return f"[{label}] Nexus view for: {text[:200]}"
