"""Reasoning Control Plane — lifecycle orchestration for thalos_prime.reasoning.

ReasoningControlPlane owns the lifecycle of the TreeOfThoughts engine and
the ChainOfVerification engine.  It enforces the six required lifecycle
methods and emits structured JSONL events for every state transition.

Control Plane component — no computational work lives here.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph
from thalos_prime.reasoning.chain_of_verification import ChainOfVerification
from thalos_prime.reasoning.schema import (
    REASONING_SCHEMA_VERSION,
    REASONING_SEED_SALT,
    ThoughtNode,
    VerificationResult,
)
from thalos_prime.reasoning.tree_of_thoughts import TreeOfThoughts


class ReasoningError(Exception):
    """Raised when the Reasoning subsystem encounters an unrecoverable error."""


class ReasoningControlPlane:
    """Lifecycle orchestrator for the Reasoning subsystem.

    Lifecycle:
        initialize() → validate() → operate() → reconcile()
        → checkpoint() → terminate()

    State surfaces:
        _tot: TreeOfThoughts (Data Plane)
        _cov: ChainOfVerification (Data Plane)
        last_thought: most recent best ThoughtNode
        last_result: most recent VerificationResult
    """

    def __init__(
        self,
        seed: int,
        workdir: str,
        *,
        max_depth: int = 5,
        beam_width: int = 3,
        score_threshold: float = 0.3,
        max_claims: int = 20,
    ) -> None:
        """Initialize the Reasoning Control Plane.

        Args:
            seed: Deterministic seed (XOR-salted to reasoning seed).
            workdir: Working directory for logs and checkpoints.
            max_depth: ToT maximum reasoning depth.
            beam_width: ToT beam width.
            score_threshold: ToT pruning threshold.
            max_claims: CoV maximum claims per answer.

        """
        self._seed = seed ^ REASONING_SEED_SALT
        self._workdir = Path(workdir)
        self._max_depth = max_depth
        self._beam_width = beam_width
        self._score_threshold = score_threshold
        self._max_claims = max_claims

        self._tot: TreeOfThoughts | None = None
        self._cov: ChainOfVerification | None = None
        self._initialized: bool = False
        self._terminated: bool = False
        self._log_path: Path | None = None

        self.last_thought: ThoughtNode | None = None
        self.last_result: VerificationResult | None = None

    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Set up Tree of Thoughts and Chain of Verification engines.

        Raises:
            ReasoningError: On initialization failure.

        """
        self._workdir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._workdir / "reasoning_events.jsonl"
        self._tot = TreeOfThoughts(
            max_depth=self._max_depth,
            beam_width=self._beam_width,
            score_threshold=self._score_threshold,
            log_path=self._log_path,
        )
        self._cov = ChainOfVerification(
            max_claims=self._max_claims,
            log_path=self._log_path,
        )
        self._initialized = True
        self._emit("lifecycle.initialize", {"seed": self._seed})

    def validate(self) -> None:
        """Validate engine configuration.

        Raises:
            ReasoningError: If validation fails.

        """
        if not self._initialized:
            raise ReasoningError("validate() called before initialize()")
        if self._tot is None or self._cov is None:
            raise ReasoningError("Engines not initialized")
        if self._max_depth < 1:
            raise ReasoningError(f"max_depth must be >= 1, got {self._max_depth}")
        if self._beam_width < 1:
            raise ReasoningError(f"beam_width must be >= 1, got {self._beam_width}")
        self._emit("lifecycle.validate", {
            "max_depth": self._max_depth,
            "beam_width": self._beam_width,
            "score_threshold": self._score_threshold,
        })

    def operate(
        self,
        query: str,
        graph: KnowledgeGraph | None = None,
    ) -> VerificationResult:
        """Run ToT then CoV for query.

        Args:
            query: The query or reasoning prompt.
            graph: Optional KnowledgeGraph for graph-aware scoring/verification.

        Returns:
            VerificationResult from the Chain of Verification.

        Raises:
            ReasoningError: If operate() called before initialize()/validate().

        """
        if not self._initialized or self._tot is None or self._cov is None:
            raise ReasoningError("operate() called before initialize()/validate()")

        best_thought = self._tot.run(query, self._seed, graph)
        self.last_thought = best_thought

        result = self._cov.verify(best_thought.thought_text, graph)
        self.last_result = result

        self._emit("lifecycle.operate", {
            "query_len": len(query),
            "best_thought_score": best_thought.score,
            "verified_claims": result.verified_claims,
            "retracted_claims": result.retracted_claims,
        })
        return result

    def reconcile(self) -> None:
        """Reconcile: no persistent state to clean up in base implementation."""
        if not self._initialized:
            raise ReasoningError("reconcile() called before initialize()")
        self._emit("lifecycle.reconcile", {})

    def checkpoint(self) -> None:
        """Serialize last result to a JSONL snapshot."""
        if not self._initialized:
            raise ReasoningError("checkpoint() called before initialize()")
        cp_dir = self._workdir / "reasoning_checkpoints"
        cp_dir.mkdir(exist_ok=True)
        ts = int(time.time() * 1000)
        cp_path = cp_dir / f"checkpoint_{ts}.json"
        payload: dict[str, Any] = {
            "seed": self._seed,
            "version": REASONING_SCHEMA_VERSION,
            "timestamp": ts,
        }
        if self.last_result is not None:
            payload["last_result_answer_id"] = self.last_result.answer_id
            payload["verified_claims"] = self.last_result.verified_claims
            payload["retracted_claims"] = self.last_result.retracted_claims
        tmp = cp_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(cp_path)
        self._emit("lifecycle.checkpoint", {"checkpoint_path": str(cp_path)})

    def terminate(self) -> None:
        """Flush log and mark as terminated."""
        self._emit("lifecycle.terminate", {})
        self._terminated = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Append a structured JSONL event to the log."""
        event = {
            "timestamp_ns": time.time_ns(),
            "version": REASONING_SCHEMA_VERSION,
            "seed": self._seed,
            "module": "reasoning",
            "event_type": event_type,
            "payload": payload,
        }
        if self._log_path is not None:
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event) + "\n")
