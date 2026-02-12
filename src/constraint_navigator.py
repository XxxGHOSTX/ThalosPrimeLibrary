import re
from typing import Dict, Optional


MAX_PEPTIDE_LENGTH = 30


def translate_constraints(text: str) -> Optional[Dict]:
    """
    Lightweight translator: turn natural language into domain + parameters.
    Currently recognizes peptide/AA queries and extracts a target length.
    """
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
