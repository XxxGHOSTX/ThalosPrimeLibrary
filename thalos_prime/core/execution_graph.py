"""Canonical execution graph wrapper backed by ThalosEngine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from thalos_prime.core.engine import EngineConfig, ThalosEngine


@dataclass
class GraphResult:
    """Execution graph result node."""

    token: str
    address: dict[str, Any]
    text: str
    score: float
    stage: str
    provenance: dict[str, Any] = field(default_factory=dict)


class ExecutionGraph:
    """Deterministic execution graph built on the canonical engine."""

    def __init__(self, mode: str = "hybrid") -> None:
        self.mode = mode

    def run(self, query: str, max_results: int = 5) -> list[GraphResult]:
        graph_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{self.mode}:{query}"))
        artifact = ThalosEngine().run(
            query,
            EngineConfig(
                seed=int(sha256(query.encode("utf-8")).hexdigest()[:8], 16),
                max_candidates=max_results,
                mode=self.mode,
                intent_override="search",
            ),
        )
        return [
            GraphResult(
                token=query,
                address={"hex": candidate.address, "url": f"https://libraryofbabel.info/book.cgi?hex={candidate.address}"},
                text=candidate.text,
                score=float(candidate.score),
                stage="canonical_engine",
                provenance={
                    "graph_id": graph_id,
                    "mode": self.mode,
                    "source": candidate.source,
                },
            )
            for candidate in artifact.candidates
        ]


def execute_graph(query: str, max_results: int = 5, mode: str = "hybrid") -> list[GraphResult]:
    """Execute deterministic graph pipeline through canonical engine."""
    return ExecutionGraph(mode=mode).run(query, max_results=max_results)
