import re

from typing import List, Dict, Optional



# Lightweight coherence scoring with configurable weights

WEIGHTS = {

    "exact": 70,

    "lang_density": 30,

    "punctuation_bonus": 10,

}



COMMON_WORDS = {

    "the", "and", "of", "to", "in", "is", "that", "it", "you", "a", "for", "on",

    "with", "as", "are", "this", "be", "or", "by", "from", "an", "at", "not"

}





def _tokenize(text: str) -> List[str]:

    return [t for t in re.split(r"\s+", text.lower()) if t]





def _punctuation_score(text: str) -> int:

    if not text:

        return 0

    punct = sum(1 for ch in text if ch in ".?!")

    sent_like = punct / max(1, len(text) / 80)  # heuristic per ~80 chars

    return min(WEIGHTS["punctuation_bonus"], int(sent_like * WEIGHTS["punctuation_bonus"]))





def score_coherence(text: str, query: str) -> int:

    if not text:

        return 0

    score = 0

    lower = text.lower()

    if query and query.lower() in lower:

        score += WEIGHTS["exact"]

    tokens = _tokenize(text)

    if tokens:

        common_hits = sum(1 for t in tokens if t in COMMON_WORDS)

        ratio = common_hits / len(tokens)

        score += min(WEIGHTS["lang_density"], int(ratio * WEIGHTS["lang_density"] * 3))

    score += _punctuation_score(text)

    return min(100, score)





def normalize_text(text: str, provider: Optional[str] = None) -> str:

    # Placeholder normalization; LLM hook can be added via provider

    return " ".join(text.split()) if text else ""





def decode_pages(pages: List[Dict], query: str, with_normalization: bool = False) -> List[Dict]:

    out = []

    for page in pages:

        raw = page.get("text", "")

        score = score_coherence(raw, query)

        norm = normalize_text(raw) if with_normalization else None

        out.append({

            "address": page.get("address"),

            "snippet": raw[:240].replace("\n", " "),

            "score": score,

            "normalized": norm,

            "source": page.get("source", "unknown"),

        })

    out.sort(key=lambda r: r.get("score", 0), reverse=True)

    return out





