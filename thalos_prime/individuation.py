"""Individuation policy primitives for Thalos Prime.

This module translates individuation into deterministic runtime signals that can
be applied repository-wide without embedding large external prose in code.

The policy focuses on:
- Distinctness: input is handled as a unique case.
- Identity continuity: query intent is preserved across transformations.
- Contextual integrity: outputs stay grounded in domain context.
- Collective coupling: support both individual and group-level utility.
- Privacy risk signaling: detect potential singling-out language.
- Recursive refinement: iterative improvement is explicit in metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

_POLICY_VERSION: Final[str] = "individuation-v1"
_PERSONAL_MARKERS: Final[frozenset[str]] = frozenset({
    "email",
    "phone",
    "address",
    "ssn",
    "passport",
    "birthday",
    "dob",
    "biometric",
    "face",
    "name",
    "person",
    "individual",
})
_COLLECTIVE_MARKERS: Final[frozenset[str]] = frozenset({
    "team",
    "community",
    "public",
    "group",
    "collective",
    "global",
    "region",
    "organization",
})
_CONTEXT_MARKERS: Final[frozenset[str]] = frozenset({
    "deterministic",
    "validation",
    "lifecycle",
    "checkpoint",
    "policy",
    "compliance",
    "reliability",
    "safety",
    "governance",
})
_IDENTITY_TOKEN_THRESHOLD: Final[int] = 3
_RECURSIVE_TOKEN_THRESHOLD: Final[int] = 4


@dataclass(frozen=True)
class IndividuationProfile:
    """Deterministic individuation profile for a query or text pair."""

    policy_version: str
    distinctness: float
    identity_continuity: float
    contextual_integrity: float
    collective_coupling: float
    privacy_singling_risk: float
    recursive_refinement: float

    def as_metadata(self) -> dict[str, float | str]:
        """Return profile as metadata-safe primitives."""
        return {
            "policy_version": self.policy_version,
            "distinctness": round(self.distinctness, 4),
            "identity_continuity": round(self.identity_continuity, 4),
            "contextual_integrity": round(self.contextual_integrity, 4),
            "collective_coupling": round(self.collective_coupling, 4),
            "privacy_singling_risk": round(self.privacy_singling_risk, 4),
            "recursive_refinement": round(self.recursive_refinement, 4),
        }


def _tokens(text: str) -> list[str]:
    return [t for t in text.lower().replace("_", " ").split() if t]


def _ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return min(1.0, max(0.0, count / total))


def build_individuation_profile(query: str, text: str = "") -> IndividuationProfile:
    """Build deterministic individuation profile from query and optional text."""
    q_tokens = _tokens(query)
    t_tokens = _tokens(text)
    total = max(1, len(q_tokens))

    unique_ratio = _ratio(len(set(q_tokens)), total)
    identity_continuity = 1.0 if len(q_tokens) >= _IDENTITY_TOKEN_THRESHOLD else 0.75

    context_hits = sum(1 for t in set(q_tokens + t_tokens) if t in _CONTEXT_MARKERS)
    contextual_integrity = max(0.4, _ratio(context_hits, 4))

    collective_hits = sum(1 for t in set(q_tokens + t_tokens) if t in _COLLECTIVE_MARKERS)
    collective_coupling = max(0.2, _ratio(collective_hits, 3))

    personal_hits = sum(1 for t in set(q_tokens + t_tokens) if t in _PERSONAL_MARKERS)
    privacy_singling_risk = _ratio(personal_hits, 3)

    # Recursive refinement is always explicit in the policy and increases when
    # we have enough lexical structure to iterate safely.
    recursive_refinement = 1.0 if len(set(q_tokens)) >= _RECURSIVE_TOKEN_THRESHOLD else 0.8

    return IndividuationProfile(
        policy_version=_POLICY_VERSION,
        distinctness=unique_ratio,
        identity_continuity=identity_continuity,
        contextual_integrity=contextual_integrity,
        collective_coupling=collective_coupling,
        privacy_singling_risk=privacy_singling_risk,
        recursive_refinement=recursive_refinement,
    )


def policy_version() -> str:
    """Return current individuation policy version string."""
    return _POLICY_VERSION
