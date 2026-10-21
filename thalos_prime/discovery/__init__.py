"""Falsifiable discovery primitives for Thalos Prime.

The package separates candidate generation from evidence-backed evaluation. It
never treats lexical coherence or an analogy as proof that a claim is true.
"""

from .engine import (
    Claim,
    Constraint,
    ConstraintResult,
    ConstraintStatus,
    DiscoveryEngine,
    DiscoveryReport,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    Observation,
)

__all__ = [
    "Claim",
    "Constraint",
    "ConstraintResult",
    "ConstraintStatus",
    "DiscoveryEngine",
    "DiscoveryReport",
    "Evidence",
    "Hypothesis",
    "HypothesisStatus",
    "Observation",
]
