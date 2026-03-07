"""Lifecycle management for Babel components."""

from __future__ import annotations

from enum import Enum, auto
from typing import Protocol


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
