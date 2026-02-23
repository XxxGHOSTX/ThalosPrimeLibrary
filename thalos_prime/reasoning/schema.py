"""Schema definitions for the thalos_prime.reasoning module.

Defines ThoughtNode, ThoughtTree, ThoughtStatus, VerificationClaim, and
VerificationResult dataclasses used by the Tree of Thoughts and Chain of
Verification engines.

Note: This is thalos_prime.reasoning (new high-level orchestration layer),
distinct from thalos_prime.library_of_sense.reasoning (existing symbolic).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum, auto

REASONING_SCHEMA_VERSION: str = "1.0"

# Seed XOR salt for reasoning module — "REAS" in ASCII hex
REASONING_SEED_SALT: int = 0x52454153


class ThoughtStatus(StrEnum):
    """Lifecycle status for a ThoughtNode in the Tree of Thoughts."""

    PENDING = auto()
    ACTIVE = auto()
    PRUNED = auto()
    TERMINAL = auto()


@dataclass
class ThoughtNode:
    """A single node in the Tree of Thoughts.

    id is SHA-256(parent_id + thought_text + str(depth)).
    """

    id: str
    parent_id: str | None
    depth: int
    thought_text: str
    score: float
    status: ThoughtStatus
    seed: int
    version: str = REASONING_SCHEMA_VERSION


@dataclass
class ThoughtTree:
    """Container for the entire Tree of Thoughts exploration."""

    root: ThoughtNode
    nodes: dict[str, ThoughtNode] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    seed: int = 0
    version: str = REASONING_SCHEMA_VERSION

    def add_node(self, node: ThoughtNode, parent_id: str | None = None) -> None:
        """Add a node to the tree and register the parent edge."""
        self.nodes[node.id] = node
        if parent_id is not None:
            self.edges.append((parent_id, node.id))


@dataclass
class VerificationClaim:
    """An atomic claim extracted from a candidate answer."""

    id: str
    answer_id: str
    claim_text: str
    verified: bool | None
    evidence: list[str]
    version: str = REASONING_SCHEMA_VERSION


@dataclass
class VerificationResult:
    """Result of Chain of Verification for a candidate answer."""

    answer_id: str
    claims: list[VerificationClaim]
    verified_claims: int
    retracted_claims: int
    final_answer: str
    version: str = REASONING_SCHEMA_VERSION
