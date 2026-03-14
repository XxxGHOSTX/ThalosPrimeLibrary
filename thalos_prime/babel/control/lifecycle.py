"""Lifecycle management for Babel components.

Defines the :class:`LifecycleComponent` Protocol aligned with the project-wide
six-method lifecycle contract and :class:`LifecycleManager` for coordinating
ordered transitions across multiple components.

Control Plane: lifecycle coordination only.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Protocol


class LifecyclePhase(Enum):
    """Phase enumeration for lifecycle state tracking."""

    CREATED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()


class LifecycleComponent(Protocol):
    """Protocol defining the six-method lifecycle contract for Babel components.

    All Babel subsystem components must implement each method with explicit
    success/failure semantics.  Identical inputs must produce identical state
    transitions (determinism contract).
    """

    def initialize(self) -> None:
        """Allocate resources and verify preconditions."""
        ...

    def validate(self) -> object:
        """Check all invariants and preconditions.

        Returns:
            Validation result (type determined by implementation).

        """
        ...

    def operate(self) -> None:
        """Execute primary work; idempotent where applicable."""
        ...

    def reconcile(self) -> None:
        """Converge component to consistent state deterministically."""
        ...

    def checkpoint(self) -> dict[str, object]:
        """Serialize state for restart; must be atomic and versioned.

        Returns:
            Serializable state representation.

        """
        ...

    def terminate(self) -> None:
        """Release all resources; must not leave orphaned state."""
        ...


class LifecycleManager:
    """Coordinate ordered lifecycle transitions across registered components.

    Components are initialized and operated in registration order; terminated
    and reconciled in reverse order to honour dependency relationships.
    """

    def __init__(self) -> None:
        """Initialise with an empty component registry."""
        self.components: list[LifecycleComponent] = []

    def initialize(self) -> None:
        """Initialize the manager; delegates to :meth:`initialize_all`."""
        self.initialize_all()

    def validate(self) -> bool:
        """Validate all registered components.

        Returns:
            True when all components validate without error.

        """
        return all(bool(component.validate()) for component in self.components)

    def operate(self) -> None:
        """Invoke :meth:`~LifecycleComponent.operate` on all components."""
        for component in self.components:
            component.operate()

    def reconcile(self) -> None:
        """Invoke :meth:`~LifecycleComponent.reconcile` on all components in reverse order."""
        for component in reversed(self.components):
            component.reconcile()

    def checkpoint(self) -> list[dict[str, object]]:
        """Collect checkpoint state from all components.

        Returns:
            List of per-component checkpoint state in registration order.

        """
        return [component.checkpoint() for component in self.components]

    def terminate(self) -> None:
        """Invoke :meth:`~LifecycleComponent.terminate` on all components in reverse order."""
        for component in reversed(self.components):
            component.terminate()

    def register(self, component: LifecycleComponent) -> None:
        """Register a component for lifecycle management.

        Args:
            component: Component implementing :class:`LifecycleComponent`.

        """
        self.components.append(component)

    def initialize_all(self) -> None:
        """Initialize all registered components in registration order."""
        for component in self.components:
            component.initialize()
