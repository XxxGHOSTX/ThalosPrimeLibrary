"""thalos_prime.reasoning — Tree of Thoughts and Chain of Verification module.

NOTE: This module (thalos_prime.reasoning) is the high-level reasoning
orchestration layer.  It is distinct from thalos_prime.library_of_sense.reasoning
which provides lower-level symbolic and constraint-solving engines.

Exports:
    ReasoningControlPlane   — Control Plane lifecycle orchestrator
    ReasoningError          — typed exception
    TreeOfThoughts          — Data Plane ToT engine
    ChainOfVerification     — Data Plane CoV engine
    ThoughtScorer           — Data Plane thought scorer
    ThoughtNode             — schema dataclass
    ThoughtTree             — schema dataclass
    ThoughtStatus           — StrEnum
    VerificationClaim       — schema dataclass
    VerificationResult      — schema dataclass
"""

from thalos_prime.reasoning.chain_of_verification import ChainOfVerification
from thalos_prime.reasoning.control_plane import ReasoningControlPlane, ReasoningError
from thalos_prime.reasoning.schema import (
    ThoughtNode,
    ThoughtStatus,
    ThoughtTree,
    VerificationClaim,
    VerificationResult,
)
from thalos_prime.reasoning.thought_scorer import ThoughtScorer
from thalos_prime.reasoning.tree_of_thoughts import TreeOfThoughts

__all__ = [
    "ChainOfVerification",
    "ReasoningControlPlane",
    "ReasoningError",
    "ThoughtNode",
    "ThoughtScorer",
    "ThoughtStatus",
    "ThoughtTree",
    "TreeOfThoughts",
    "VerificationClaim",
    "VerificationResult",
]
