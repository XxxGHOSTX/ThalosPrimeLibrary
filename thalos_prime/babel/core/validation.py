"""Validation utilities for Babel subsystem.

Provides :class:`ValidationResult`, the :class:`Validator` Protocol, and
:class:`SystemValidator` for aggregating multiple validators.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    message: str
    details: dict[str, Any]


class Validator(Protocol):
    """Protocol for components that participate in the six-method lifecycle."""

    def initialize(self) -> None:
        """Allocate resources and verify preconditions."""
        ...

    def validate(self) -> ValidationResult:
        """Return a :class:`ValidationResult` for this component."""
        ...

    def operate(self) -> None:
        """Execute primary work; idempotent where applicable."""
        ...

    def reconcile(self) -> None:
        """Converge to consistent state deterministically."""
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


class SystemValidator:
    """Run registered validators and aggregate results."""

    def __init__(self) -> None:
        """Initialize with an empty validator registry."""
        self.validators: list[Validator] = []

    def register(self, validator: Validator) -> None:
        """Register *validator* for inclusion in :meth:`validate_all`.

        Args:
            validator: Component implementing :class:`Validator`.

        """
        self.validators.append(validator)

    def validate_all(self) -> list[ValidationResult]:
        """Run all registered validators and return their results.

        Returns:
            List of :class:`ValidationResult` in registration order.

        """
        return [validator.validate() for validator in self.validators]

    def is_valid(self) -> bool:
        """Return True only when all validators pass.

        Returns:
            True if every :class:`ValidationResult` has ``passed=True``.

        """
        return all(result.passed for result in self.validate_all())
