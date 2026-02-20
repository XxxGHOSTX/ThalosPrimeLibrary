"""Library of Sense - Lifecycle state management.

Provides the LifecycleState enum and LifecycleEvent dataclass for tracking
subsystem lifecycle transitions with deterministic event logging.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class LifecycleState(str, Enum):
    """Enumeration of valid lifecycle states for Library of Sense subsystems."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    VALIDATING = "validating"
    READY = "ready"
    OPERATING = "operating"
    RECONCILING = "reconciling"
    CHECKPOINTING = "checkpointing"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class LifecycleEvent:
    """Records a lifecycle state transition with metadata for deterministic replay."""

    subsystem: str
    from_state: LifecycleState
    to_state: LifecycleState
    seed: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: str = ""

    def to_dict(self) -> dict[str, object]:
        """Serialize lifecycle event to dictionary.

        Returns:
            Dictionary representation of this event.
        """
        return {
            "subsystem": self.subsystem,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "seed": self.seed,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class SubsystemLifecycle:
    """Manages lifecycle state transitions and event logging for a subsystem."""

    def __init__(self, subsystem_name: str, seed: int = 0) -> None:
        """Initialize lifecycle manager for a named subsystem.

        Args:
            subsystem_name: Unique identifier for the subsystem.
            seed: Deterministic seed for replay identification.
        """
        self._subsystem_name = subsystem_name
        self._seed = seed
        self._state = LifecycleState.UNINITIALIZED
        self._events: list[LifecycleEvent] = []

    @property
    def state(self) -> LifecycleState:
        """Current lifecycle state.

        Returns:
            Current LifecycleState value.
        """
        return self._state

    def transition(self, new_state: LifecycleState, details: str = "") -> None:
        """Transition to a new lifecycle state, logging the event.

        Args:
            new_state: The target lifecycle state.
            details: Optional details about this transition.
        """
        event = LifecycleEvent(
            subsystem=self._subsystem_name,
            from_state=self._state,
            to_state=new_state,
            seed=self._seed,
            details=details,
        )
        self._events.append(event)
        logger.info(
            "Lifecycle transition: %s -> %s [%s] seed=%d",
            self._state.value,
            new_state.value,
            self._subsystem_name,
            self._seed,
        )
        self._state = new_state

    def get_events(self) -> list[LifecycleEvent]:
        """Return all recorded lifecycle events.

        Returns:
            List of LifecycleEvent records in chronological order.
        """
        return list(self._events)


__all__ = ["LifecycleState", "LifecycleEvent", "SubsystemLifecycle"]
