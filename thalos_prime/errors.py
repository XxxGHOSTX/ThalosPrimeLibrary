"""Typed exception classes for ThalosPrime.

All exceptions include deterministic state snapshots and checkpoint payloads
for full observability and reproducibility.
"""

from __future__ import annotations

from typing import Any


class ThalosBaseError(Exception):
    """Base exception for all ThalosPrime typed errors."""

    def __init__(self, message: str, *, state_snapshot: dict[str, Any] | None = None) -> None:
        """Initialize with message and optional state snapshot.

        Args:
            message: Human-readable error description.
            state_snapshot: Deterministic serializable snapshot of system state
                at the time of the error, for replay and audit.

        """
        super().__init__(message)
        self.state_snapshot: dict[str, Any] = state_snapshot or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error and its state snapshot."""
        return {
            "error": type(self).__name__,
            "message": str(self),
            "state_snapshot": self.state_snapshot,
        }


class CoherenceThresholdError(ThalosBaseError):
    """Raised when coherence threshold cannot be met within the time/attempt budget.

    Per the determinism rules, this error must be raised rather than silently
    returning below-threshold results.  The caller receives the full state
    snapshot including the checkpoint payload for replay and audit.
    """

    def __init__(
        self,
        *,
        min_score: float,
        best_score: float,
        attempts: int,
        time_budget_s: float,
        checkpoint: dict[str, Any],
        mode: str,
    ) -> None:
        """Initialize CoherenceThresholdError.

        Args:
            min_score: Required minimum coherence score.
            best_score: Best score achieved across all attempts.
            attempts: Number of generation attempts made.
            time_budget_s: Wall-clock seconds elapsed.
            checkpoint: Full serializable checkpoint of task state.
            mode: Search mode that was in use.

        """
        message = (
            f"Coherence threshold not met: required >= {min_score:.1f}, "
            f"best achieved {best_score:.1f} across {attempts} attempt(s) "
            f"in {time_budget_s:.1f}s (mode={mode!r}). "
            "Use mode='generative' or lower min_score to allow below-threshold results."
        )
        super().__init__(
            message,
            state_snapshot={
                "min_score": min_score,
                "best_score": best_score,
                "attempts": attempts,
                "time_budget_s": time_budget_s,
                "mode": mode,
                "checkpoint": checkpoint,
            },
        )
        self.min_score = min_score
        self.best_score = best_score
        self.attempts = attempts
        self.time_budget_s = time_budget_s
        self.checkpoint = checkpoint
        self.mode = mode
