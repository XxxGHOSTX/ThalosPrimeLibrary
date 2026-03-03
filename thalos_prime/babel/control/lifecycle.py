"""Lifecycle management for Babel components."""

from __future__ import annotations

from enum import Enum, auto
from typing import Protocol


class LifecyclePhase(Enum):
    """Lifecycle phases for components."""

    CREATED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()


class LifecycleComponent(Protocol):
    """Protocol for lifecycle-managed components."""

    def initialize(self) -> None:
        """Initialize the component."""
        ...

    def start(self) -> None:
        """Start the component."""
        ...

    def stop(self) -> None:
        """Stop the component."""
        ...

    def cleanup(self) -> None:
        """Clean up resources."""
        ...


class LifecycleManager:
    """Manage ordered lifecycle transitions."""

    def __init__(self) -> None:
        """Initialize the lifecycle manager."""
        self.components: list[LifecycleComponent] = []

    def register(self, component: LifecycleComponent) -> None:
        """Register a lifecycle component."""
        self.components.append(component)

    def initialize_all(self) -> None:
        """Initialize all components."""
        for component in self.components:
            component.initialize()

    def start_all(self) -> None:
        """Start all components in order."""
        for component in self.components:
            component.start()

    def stop_all(self) -> None:
        """Stop all components in reverse order."""
        for component in reversed(self.components):
            component.stop()

    def cleanup_all(self) -> None:
        """Clean up all components in reverse order."""
        for component in reversed(self.components):
            component.cleanup()
