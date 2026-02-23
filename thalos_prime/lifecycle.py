"""Thalos Prime - Lifecycle Protocol and Base Component.

Defines the authoritative LifecycleProtocol that all subsystems must implement,
and BaseLifecycleComponent as a concrete abstract base class providing
structured lifecycle state tracking and deterministic event logging.

Control Plane boundary: this module defines enforcement contracts only.
No data-plane computational logic belongs here.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from thalos_prime.library_of_sense.core.interfaces import ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class LifecycleEvent:
    """Records a lifecycle method invocation with metadata for deterministic replay."""

    component: str
    method: str
    seed: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: str = ""

    def to_dict(self) -> dict[str, object]:
        """Serialize lifecycle event to dictionary.

        Returns:
            Dictionary representation of this event.

        """
        return {
            "component": self.component,
            "method": self.method,
            "seed": self.seed,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


@runtime_checkable
class LifecycleProtocol(Protocol):
    """Authoritative lifecycle protocol for all Thalos Prime subsystems.

    All subsystems — control-plane and data-plane — must implement this protocol.
    Identical lifecycle transitions with identical inputs must produce identical
    state sequences (deterministic contract).
    """

    def initialize(self) -> None:
        """Allocate resources and verify preconditions.

        Must succeed entirely or raise a typed exception. No partial
        initialization is permitted.
        """
        ...

    def validate(self) -> ValidationResult:
        """Check all invariants and preconditions.

        Returns:
            ValidationResult indicating success or describing failure.

        """
        ...

    def operate(self) -> None:
        """Execute primary work.

        Must be idempotent where applicable. No lifecycle coordination
        logic belongs here.
        """
        ...

    def reconcile(self) -> None:
        """Converge subsystem to consistent state.

        Must deterministically succeed or halt with full state capture.
        """
        ...

    def checkpoint(self) -> dict[str, object]:
        """Serialize full state for restart.

        Must be atomic and versioned.

        Returns:
            Serializable dict with complete subsystem state.

        """
        ...

    def terminate(self) -> None:
        """Release all resources.

        Must not leave orphaned state.
        """
        ...


class BaseLifecycleComponent(ABC):
    """Abstract base class implementing LifecycleProtocol with common lifecycle plumbing.

    Provides structured event logging and state tracking. Subclasses must
    implement all abstract methods to satisfy the lifecycle contract.
    """

    def __init__(self, component_name: str, seed: int = 0) -> None:
        """Initialize lifecycle state tracking.

        Args:
            component_name: Unique identifier for this component.
            seed: Deterministic seed for replay identification.

        """
        self._component_name = component_name
        self._seed = seed
        self._initialized: bool = False
        self._events: list[LifecycleEvent] = []

    def _emit_event(self, method: str, details: str = "") -> None:
        """Emit a structured lifecycle event log entry.

        Args:
            method: Name of the lifecycle method being invoked.
            details: Optional human-readable details about this invocation.

        """
        event = LifecycleEvent(
            component=self._component_name,
            method=method,
            seed=self._seed,
            details=details,
        )
        self._events.append(event)
        logger.info(
            "Lifecycle event: %s.%s() seed=%d details=%s",
            self._component_name,
            method,
            self._seed,
            details,
        )

    def get_events(self) -> list[LifecycleEvent]:
        """Return all recorded lifecycle events in chronological order.

        Returns:
            Immutable copy of the lifecycle event log.

        """
        return list(self._events)

    @abstractmethod
    def initialize(self) -> None:
        """Allocate resources and verify preconditions."""

    @abstractmethod
    def validate(self) -> ValidationResult:
        """Check all invariants and preconditions.

        Returns:
            ValidationResult describing whether invariants hold.

        """

    @abstractmethod
    def operate(self) -> None:
        """Execute primary work."""

    @abstractmethod
    def reconcile(self) -> None:
        """Converge subsystem to consistent state."""

    @abstractmethod
    def checkpoint(self) -> dict[str, object]:
        """Serialize full state for restart.

        Returns:
            Serializable dict with complete subsystem state.

        """

    @abstractmethod
    def terminate(self) -> None:
        """Release all resources."""


__all__ = ["BaseLifecycleComponent", "LifecycleEvent", "LifecycleProtocol"]
