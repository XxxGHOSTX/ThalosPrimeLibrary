"""Lifecycle management for Babel components."""

from __future__ import annotations

from enum import Enum, auto
from typing import Protocol


class LifecyclePhase(Enum):
    """Enumeration of lifecycle phases."""

    CREATED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()


class LifecycleComponent(Protocol):
    """Protocol for all Babel lifecycle components."""

    def initialize(self) -> None:
        """Set up resources and initial state."""
        ...

    def validate(self) -> None:
        """Check invariants and preconditions."""
        ...

    def operate(self) -> None:
        """Execute primary work."""
        ...

    def reconcile(self) -> None:
        """Converge to consistent state."""
        ...

    def checkpoint(self) -> None:
        """Serialize state for restart."""
        ...

    def terminate(self) -> None:
        """Clean up resources."""
        ...

    def start(self) -> None:
        """Start the component."""
        ...

    def stop(self) -> None:
        """Stop the component."""
        ...

    def cleanup(self) -> None:
        """Clean up after the component."""
        ...


class LifecycleManager:
    """Manage ordered lifecycle transitions."""

    def __init__(self) -> None:
        """Initialize the lifecycle manager."""
        self.components: list[LifecycleComponent] = []

    def register(self, component: LifecycleComponent) -> None:
        """Register a lifecycle component.

        Args:
            component: The component to register.

        """
        self.components.append(component)

    def initialize(self) -> None:
        """Initialize all registered components."""
        for component in self.components:
            component.initialize()

    def validate(self) -> None:
        """Validate all registered components."""
        for component in self.components:
            component.validate()

    def operate(self) -> None:
        """Operate all registered components."""
        for component in self.components:
            component.operate()

    def reconcile(self) -> None:
        """Reconcile all registered components."""
        for component in self.components:
            component.reconcile()

    def checkpoint(self) -> None:
        """Checkpoint all registered components."""
        for component in self.components:
            component.checkpoint()

    def terminate(self) -> None:
        """Terminate all registered components in reverse order."""
        for component in reversed(self.components):
            component.terminate()

    def initialize_all(self) -> None:
        """Initialize all components (alias for initialize())."""
        self.initialize()

    def start_all(self) -> None:
        """Start all registered components."""
        for component in self.components:
            component.start()

    def stop_all(self) -> None:
        """Stop all registered components in reverse order."""
        for component in reversed(self.components):
            component.stop()

    def cleanup_all(self) -> None:
        """Clean up all registered components in reverse order."""
        for component in reversed(self.components):
            component.cleanup()
