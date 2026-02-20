"""Library of Sense - State Manager.

Manages the persistent, observable, and serializable state for the
Library of Sense subsystem with full lifecycle support.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Final

from thalos_prime.library_of_sense.core.lifecycle import LifecycleState, SubsystemLifecycle

logger = logging.getLogger(__name__)

_SUBSYSTEM_NAME: Final[str] = "library_of_sense.state_manager"


@dataclass
class LibrarySenseState:
    """Observable, serializable state for the Library of Sense subsystem."""

    version: int = 1
    seed: int = 0
    query_count: int = 0
    retrieval_count: int = 0
    synthesis_count: int = 0
    error_count: int = 0
    active_sources: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, object]:
        """Serialize state to dictionary.

        Returns:
            Dictionary representation of current state.
        """
        return {
            "version": self.version,
            "seed": self.seed,
            "query_count": self.query_count,
            "retrieval_count": self.retrieval_count,
            "synthesis_count": self.synthesis_count,
            "error_count": self.error_count,
            "active_sources": list(self.active_sources),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class StateManager:
    """Manages Library of Sense subsystem state with full lifecycle support.

    Provides observable, serializable state management with deterministic
    checkpointing and reconciliation.
    """

    def __init__(self, seed: int = 0) -> None:
        """Initialize the state manager.

        Args:
            seed: Deterministic seed for replay identification.
        """
        self._seed = seed
        self._state = LibrarySenseState(seed=seed)
        self._lifecycle = SubsystemLifecycle(_SUBSYSTEM_NAME, seed=seed)
        self._checkpoint_count = 0

    def initialize(self) -> None:
        """Initialize the state manager and transition to initialized state.

        Sets up initial state and transitions lifecycle to INITIALIZED.
        """
        self._lifecycle.transition(LifecycleState.INITIALIZING, "Starting initialization")
        self._state = LibrarySenseState(seed=self._seed)
        self._checkpoint_count = 0
        self._lifecycle.transition(LifecycleState.INITIALIZED, "Initialization complete")
        logger.info("StateManager initialized with seed=%d", self._seed)

    def validate(self) -> None:
        """Validate state invariants and transition to READY state.

        Raises:
            RuntimeError: If the state is inconsistent.
        """
        self._lifecycle.transition(LifecycleState.VALIDATING, "Validating state invariants")
        if self._state.version < 1:
            msg = f"Invalid state version: {self._state.version}"
            raise RuntimeError(msg)
        if self._state.query_count < 0:
            msg = f"Invalid query count: {self._state.query_count}"
            raise RuntimeError(msg)
        self._lifecycle.transition(LifecycleState.READY, "Validation complete")
        logger.info("StateManager validation passed")

    def operate(self) -> None:
        """Transition to OPERATING state for normal operation.

        Marks the manager as actively processing queries.
        """
        self._lifecycle.transition(LifecycleState.OPERATING, "Entering operation mode")
        logger.info("StateManager operating, query_count=%d", self._state.query_count)

    def reconcile(self) -> None:
        """Reconcile state to ensure consistency.

        Corrects any counter inconsistencies and transitions back to READY.
        """
        self._lifecycle.transition(LifecycleState.RECONCILING, "Reconciling state")
        if self._state.error_count < 0:
            self._state.error_count = 0
        if self._state.query_count < 0:
            self._state.query_count = 0
        self._state.updated_at = datetime.now(timezone.utc)
        self._lifecycle.transition(LifecycleState.READY, "Reconciliation complete")
        logger.info("StateManager reconciliation complete")

    def checkpoint(self) -> None:
        """Serialize and record current state as a versioned checkpoint.

        Emits a structured log event with full state snapshot for replay.
        """
        self._lifecycle.transition(LifecycleState.CHECKPOINTING, "Creating checkpoint")
        self._checkpoint_count += 1
        snapshot = self._state.to_dict()
        logger.info(
            "StateManager checkpoint #%d: seed=%d version=%d queries=%d",
            self._checkpoint_count,
            self._seed,
            self._state.version,
            self._state.query_count,
        )
        logger.debug("StateManager checkpoint snapshot: %s", snapshot)
        self._lifecycle.transition(LifecycleState.READY, "Checkpoint complete")

    def terminate(self) -> None:
        """Terminate the state manager and release resources.

        Logs final state and transitions to TERMINATED lifecycle state.
        """
        self._lifecycle.transition(LifecycleState.TERMINATING, "Terminating")
        logger.info(
            "StateManager terminating: total_queries=%d errors=%d",
            self._state.query_count,
            self._state.error_count,
        )
        self._lifecycle.transition(LifecycleState.TERMINATED, "Termination complete")

    def increment_query_count(self) -> None:
        """Increment the query counter and update timestamp."""
        self._state.query_count += 1
        self._state.updated_at = datetime.now(timezone.utc)

    def increment_retrieval_count(self) -> None:
        """Increment the retrieval counter and update timestamp."""
        self._state.retrieval_count += 1
        self._state.updated_at = datetime.now(timezone.utc)

    def increment_synthesis_count(self) -> None:
        """Increment the synthesis counter and update timestamp."""
        self._state.synthesis_count += 1
        self._state.updated_at = datetime.now(timezone.utc)

    def increment_error_count(self) -> None:
        """Increment the error counter and update timestamp."""
        self._state.error_count += 1
        self._state.updated_at = datetime.now(timezone.utc)

    def add_source(self, source_name: str) -> None:
        """Register an active retrieval source.

        Args:
            source_name: Identifier of the retrieval source to register.
        """
        if source_name not in self._state.active_sources:
            self._state.active_sources.append(source_name)

    def get_state(self) -> LibrarySenseState:
        """Return the current state snapshot.

        Returns:
            Current LibrarySenseState instance.
        """
        return self._state

    @property
    def lifecycle_state(self) -> LifecycleState:
        """Current lifecycle state of the manager.

        Returns:
            Current LifecycleState value.
        """
        return self._lifecycle.state


__all__ = ["LibrarySenseState", "StateManager"]
