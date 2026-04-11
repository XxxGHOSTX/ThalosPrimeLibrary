"""Lifecycle management for Babel components."""

from __future__ import annotations

from enum import Enum, auto
from typing import Protocol


class LifecyclePhase(Enum):
    CREATED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()


class LifecycleComponent(Protocol):
    def initialize(self) -> None:
        ...

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def cleanup(self) -> None:
        ...


class LifecycleManager:
    """Manage ordered lifecycle transitions."""

    def __init__(self) -> None:
        self.components: list[LifecycleComponent] = []

    def register(self, component: LifecycleComponent) -> None:
        self.components.append(component)

    def initialize_all(self) -> None:
        for component in self.components:
            component.initialize()

    def start_all(self) -> None:
        for component in self.components:
            component.start()

    def stop_all(self) -> None:
        for component in reversed(self.components):
            component.stop()

    def cleanup_all(self) -> None:
        for component in reversed(self.components):
            component.cleanup()
