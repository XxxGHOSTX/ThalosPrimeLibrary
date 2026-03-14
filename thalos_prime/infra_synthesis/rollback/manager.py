"""Rollback manager for infra-synthesis.

Captures pre-deploy state snapshots and restores them via the state
backend when a rollback is required.

Control Plane: lifecycle coordination for rollback operations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from thalos_prime.infra_synthesis.rollback.snapshot import SnapshotManager

if TYPE_CHECKING:
    from thalos_prime.infra_synthesis.state.backend import StateBackend

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages pre-deploy snapshots and rollback operations.

    Usage::

        backend = LocalStateBackend()
        manager = RollbackManager(backend)
        manager.pre_deploy("v1.2.3", schema)
        # ... deploy ...
        manager.rollback("v1.2.3")

    Args:
        backend: State backend for snapshot persistence.

    """

    def __init__(self, backend: StateBackend) -> None:
        """Initialise with *backend*.

        Args:
            backend: State backend for snapshot persistence.

        """
        self._snapshot_manager = SnapshotManager(backend)
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the rollback manager."""
        self._initialized = True
        logger.debug("RollbackManager: initialized")

    def validate(self) -> None:
        """Validate that the rollback manager is ready.

        Raises:
            RuntimeError: When the manager has not been initialized.

        """
        if not self._initialized:
            msg = "RollbackManager not initialized; call initialize() first"
            raise RuntimeError(msg)

    def operate(self) -> None:
        """Execute primary work (no background operation; no-op)."""

    def reconcile(self) -> None:
        """Reconcile rollback manager state (stateless; no-op)."""

    def checkpoint(self) -> None:
        """Serialize rollback manager state (snapshot state is held by backend)."""

    def terminate(self) -> None:
        """Terminate the rollback manager and reset state."""
        self._initialized = False
        logger.debug("RollbackManager: terminated")

    def pre_deploy(self, deploy_key: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Capture a pre-deploy snapshot of *schema*.

        Call this before applying any infrastructure changes.

        Args:
            deploy_key: Unique key identifying this deployment (e.g. version tag).
            schema: Current validated schema dict.

        Returns:
            The stored snapshot dict.

        """
        logger.info("RollbackManager: capturing pre-deploy snapshot '%s'", deploy_key)
        snapshot = self._snapshot_manager.capture(f"pre-deploy:{deploy_key}", schema)
        logger.info("RollbackManager: pre-deploy snapshot '%s' captured", deploy_key)
        return snapshot

    def rollback(self, deploy_key: str) -> dict[str, Any]:
        """Restore the pre-deploy snapshot for *deploy_key*.

        Args:
            deploy_key: Key used when :meth:`pre_deploy` was called.

        Returns:
            Restored schema snapshot dict.

        Raises:
            KeyError: When no pre-deploy snapshot exists for *deploy_key*.

        """
        logger.info("RollbackManager: rolling back to pre-deploy snapshot '%s'", deploy_key)
        snapshot = self._snapshot_manager.restore(f"pre-deploy:{deploy_key}")
        logger.info("RollbackManager: rollback to '%s' complete", deploy_key)
        return snapshot


__all__ = ["RollbackManager"]
