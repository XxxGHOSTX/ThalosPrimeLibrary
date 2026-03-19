"""Thalos Prime - Belief State Tracker.

Data Plane component that maintains a deterministic belief store mapping
keys to values with confidence scores. Beliefs are versioned and all
mutations are logged for replay.

Data Plane boundary: tracks agent knowledge state only — no lifecycle
orchestration or action coordination belongs here.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from thalos_prime.library_of_sense.core.interfaces import ValidationResult
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)


@dataclass
class BeliefEntry:
    """A single belief held by the agent.

    Attributes:
        key: Unique identifier for this belief.
        value: The believed content (arbitrary string).
        confidence: Confidence score in [0.0, 1.0].
        version: Monotonically increasing revision counter.
        updated_at: ISO-8601 timestamp of last update.
        source: Origin of this belief (e.g. retrieval source name).

    """

    key: str
    value: str
    confidence: float
    version: int = 1
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = ""

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this BeliefEntry.

        """
        return {
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "version": self.version,
            "updated_at": self.updated_at,
            "source": self.source,
        }


class BeliefTracker(BaseLifecycleComponent):
    """Deterministic belief state tracker.

    Maintains a key→BeliefEntry store with versioned updates, confidence
    thresholds, and state hashing for checkpoint/restore. Identical
    sequences of update calls produce identical final states.
    """

    def __init__(self, seed: int = 0, confidence_threshold: float = 0.0) -> None:
        """Initialize the belief tracker.

        Args:
            seed: Deterministic seed for replay identification.
            confidence_threshold: Minimum confidence for a belief to be
                considered active. Beliefs below this are retained but
                flagged inactive in queries.

        """
        super().__init__("BeliefTracker", seed=seed)
        self._confidence_threshold = confidence_threshold
        self._beliefs: dict[str, BeliefEntry] = {}
        self._update_count: int = 0

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the belief tracker and reset state."""
        self._beliefs = {}
        self._update_count = 0
        self._initialized = True
        self._emit_event("initialize", "beliefs cleared, initialized=True")
        logger.debug("BeliefTracker initialized")

    def validate(self) -> ValidationResult:
        """Validate that the belief tracker is ready.

        Returns:
            ValidationResult indicating readiness.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="BeliefTracker not initialized; call initialize() first",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"BeliefTracker ready: beliefs={len(self._beliefs)} "
                f"updates={self._update_count}"
            ),
        )

    def operate(self) -> None:
        """Log current statistics. Idempotent."""
        self._emit_event(
            "operate",
            f"beliefs={len(self._beliefs)} updates={self._update_count}",
        )

    def reconcile(self) -> None:
        """Reconcile counters to non-negative values."""
        self._update_count = max(self._update_count, 0)
        self._emit_event(
            "reconcile",
            f"beliefs={len(self._beliefs)} updates={self._update_count}",
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialize belief tracker state.

        Returns:
            Dict with component name, seed, belief count, and state hash.

        """
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "belief_count": len(self._beliefs),
            "update_count": self._update_count,
            "state_hash": self.state_hash(),
        }
        self._emit_event("checkpoint", f"beliefs={len(self._beliefs)}")
        return state

    def terminate(self) -> None:
        """Reset belief tracker state."""
        self._beliefs = {}
        self._update_count = 0
        self._initialized = False
        self._emit_event("terminate", "beliefs cleared, initialized=False")
        logger.debug("BeliefTracker terminated")

    # ------------------------------------------------------------------
    # Data Plane methods
    # ------------------------------------------------------------------

    def update_belief(
        self,
        key: str,
        value: str,
        confidence: float,
        source: str = "",
    ) -> BeliefEntry:
        """Add or update a belief in the store.

        If the key already exists its version is incremented.

        Args:
            key: Unique identifier for the belief.
            value: The belief content.
            confidence: Confidence score in [0.0, 1.0].
            source: Origin label for provenance tracking.

        Returns:
            The created or updated BeliefEntry.

        """
        clamped = max(0.0, min(1.0, confidence))
        existing = self._beliefs.get(key)
        version = (existing.version + 1) if existing else 1
        entry = BeliefEntry(
            key=key,
            value=value,
            confidence=clamped,
            version=version,
            source=source,
        )
        self._beliefs[key] = entry
        self._update_count += 1
        logger.debug(
            "BeliefTracker.update_belief: key=%r confidence=%.2f version=%d",
            key,
            clamped,
            version,
        )
        return entry

    def get_belief(self, key: str) -> BeliefEntry | None:
        """Retrieve a belief by key.

        Args:
            key: The belief key to look up.

        Returns:
            The BeliefEntry if found, else None.

        """
        return self._beliefs.get(key)

    def remove_belief(self, key: str) -> bool:
        """Remove a belief from the store.

        Args:
            key: The belief key to remove.

        Returns:
            True if the key existed and was removed, False otherwise.

        """
        if key in self._beliefs:
            del self._beliefs[key]
            self._update_count += 1
            return True
        return False

    def query_beliefs(
        self,
        min_confidence: float | None = None,
    ) -> list[BeliefEntry]:
        """Return beliefs filtered by confidence.

        Args:
            min_confidence: If provided, only beliefs at or above this
                threshold are returned. If None, uses the instance
                confidence_threshold.

        Returns:
            Sorted list of BeliefEntry (by key for determinism).

        """
        threshold = (
            min_confidence if min_confidence is not None else self._confidence_threshold
        )
        entries = [
            entry
            for entry in self._beliefs.values()
            if entry.confidence >= threshold
        ]
        return sorted(entries, key=lambda e: e.key)

    def state_hash(self) -> str:
        """Compute a deterministic hash of the current belief state.

        Returns:
            Hex digest string of the SHA-256 hash over sorted beliefs.

        """
        hasher = hashlib.sha256()
        for key in sorted(self._beliefs):
            entry = self._beliefs[key]
            hasher.update(f"{key}:{entry.value}:{entry.confidence}:{entry.version}".encode())
        return hasher.hexdigest()

    @property
    def belief_count(self) -> int:
        """Return the number of beliefs currently held."""
        return len(self._beliefs)


__all__ = ["BeliefEntry", "BeliefTracker"]
