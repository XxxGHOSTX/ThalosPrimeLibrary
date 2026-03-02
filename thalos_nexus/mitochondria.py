"""Thalos NEXUS — Mitochondria: budget governor.

Tracks wall-clock time budgets for gate execution.  Provides:

- ``BudgetGovernor``: start/query/over-budget check and per-gate allocation.

The governor does not enforce termination; it provides signals that the
gate runner or orchestrator can use to make stop/continue decisions.

Control Plane boundary: budget decisions only; no gate execution here.
"""

from __future__ import annotations

import time


class BudgetExhaustedError(RuntimeError):
    """Raised when requesting an allocation from an exhausted budget."""


class BudgetGovernor:
    """Wall-clock time budget tracker for gate-suite execution.

    Parameters
    ----------
    total_budget_seconds:
        Maximum wall-clock seconds allowed for the entire gate suite.

    Examples
    --------
    >>> gov = BudgetGovernor(total_budget_seconds=120.0)
    >>> gov.start()
    >>> alloc = gov.allocate_gate_budget("my-gate")
    >>> gov.is_over_budget()
    False

    """

    def __init__(self, total_budget_seconds: float) -> None:
        """Initialise the governor with a total budget."""
        if total_budget_seconds <= 0:
            msg = f"total_budget_seconds must be positive; got {total_budget_seconds}"
            raise ValueError(msg)
        self._total_budget: float = total_budget_seconds
        self._start_time: float | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the budget clock.  Must be called before querying remaining time."""
        self._start_time = time.monotonic()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def elapsed_seconds(self) -> float:
        """Return seconds elapsed since ``start()`` was called.

        Returns 0.0 if ``start()`` has not been called.
        """
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def remaining_seconds(self) -> float:
        """Return budget seconds remaining (never negative).

        Returns the full budget if ``start()`` has not been called.
        """
        return max(0.0, self._total_budget - self.elapsed_seconds())

    def is_over_budget(self) -> bool:
        """Return ``True`` if the elapsed time exceeds the total budget."""
        return self.elapsed_seconds() > self._total_budget

    # ------------------------------------------------------------------
    # Gate budget allocation
    # ------------------------------------------------------------------

    def allocate_gate_budget(self, gate_name: str) -> float:
        """Return the number of seconds to allocate to the named gate.

        The allocation is the remaining budget (at most ``total_budget``).
        Raises ``BudgetExhaustedError`` if no budget remains.

        Parameters
        ----------
        gate_name:
            Name of the gate requesting an allocation (used in the error
            message only).

        Returns
        -------
        float
            Seconds available for this gate.

        Raises
        ------
        BudgetExhaustedError
            If the remaining budget is zero.

        """
        remaining = self.remaining_seconds()
        if remaining == 0.0:
            msg = f"Budget exhausted; cannot allocate time for gate '{gate_name}'"
            raise BudgetExhaustedError(msg)
        return remaining

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return a concise string representation."""
        return (
            f"BudgetGovernor(total={self._total_budget}s, "
            f"elapsed={self.elapsed_seconds():.2f}s)"
        )
