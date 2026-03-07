"""Lifecycle management for Babel components."""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Protocol

_log = logging.getLogger(__name__)


class LifecyclePhase(Enum):
    """Ordered phases of a component's lifecycle."""

    CREATED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()


class LifecycleComponent(Protocol):
    """Protocol defining the lifecycle interface for managed components."""

    def initialize(self) -> None:
        """Set up resources and establish initial state."""
        ...

    def validate(self) -> None:
        """Verify all invariants and preconditions are satisfied."""
        ...

    def operate(self) -> None:
        """Execute primary operational work."""
        ...

    def reconcile(self) -> None:
        """Converge component to a consistent state."""
        ...

    def checkpoint(self) -> dict[str, object]:
        """Serialize component state for restart."""
        ...

    def terminate(self) -> None:
        """Release all resources and finalize shutdown."""
        ...

    def start(self) -> None:
        """Begin normal operation."""
        ...

    def stop(self) -> None:
        """Cease operation and release active resources."""
        ...

    def cleanup(self) -> None:
        """Release all remaining resources and finalize shutdown."""
        ...


class LifecycleManager:
    """Manage ordered lifecycle transitions."""

    def __init__(self) -> None:
        """Initialize with an empty component registry."""
        self.components: list[LifecycleComponent] = []

    def register(self, component: LifecycleComponent) -> None:
        """Append a component to the ordered registry."""
        self.components.append(component)

    def initialize_all(self) -> None:
        """Call initialize() on every registered component in registration order."""
        for component in self.components:
            component.initialize()

    def start_all(self) -> None:
        """Call start() on every registered component in registration order."""
        for component in self.components:
            component.start()

    def stop_all(self) -> None:
        """Call stop() on every registered component in reverse registration order."""
        for component in reversed(self.components):
            component.stop()

    def cleanup_all(self) -> None:
        """Call cleanup() on every registered component in reverse registration order."""
        for component in reversed(self.components):
            component.cleanup()

    def initialize(self) -> None:
        """Initialize all registered components in registration order."""
        self.initialize_all()
        _log.info("LifecycleManager initialized: %d components", len(self.components))

    def validate(self) -> None:
        """Verify all registered components satisfy their lifecycle invariants."""
        for component in self.components:
            component.validate()

    def operate(self) -> None:
        """Start all registered components in registration order."""
        self.start_all()

    def reconcile(self) -> None:
        """No-op reconciliation; component ordering is enforced externally."""

    def checkpoint(self) -> dict[str, object]:
        """Return a snapshot of lifecycle manager state."""
        return {"component_count": len(self.components)}

    def terminate(self) -> None:
        """Stop and clean up all registered components."""
        self.stop_all()
        self.cleanup_all()
        _log.info("LifecycleManager terminated")
