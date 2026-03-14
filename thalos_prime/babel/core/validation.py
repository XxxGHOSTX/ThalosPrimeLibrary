"""Validation utilities for Babel subsystem."""

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
    """Protocol for validator components with full lifecycle support."""

    def validate(self) -> ValidationResult:
        """Run the validation check.

        Returns:
            ValidationResult indicating pass/fail.

        """
        ...

    def initialize(self) -> None:
        """Initialize the validator."""
        ...

    def operate(self) -> None:
        """Execute primary work."""
        ...

    def reconcile(self) -> None:
        """Reconcile validator state."""
        ...

    def checkpoint(self) -> None:
        """Serialize validator state."""
        ...

    def terminate(self) -> None:
        """Terminate and clean up the validator."""
        ...


class SystemValidator:
    """Run registered validators and aggregate results."""

    def __init__(self) -> None:
        """Initialize the system validator."""
        self.validators: list[Validator] = []

    def register(self, validator: Validator) -> None:
        """Register a validator component.

        Args:
            validator: Validator to add to the registry.

        """
        self.validators.append(validator)

    def validate_all(self) -> list[ValidationResult]:
        """Run all registered validators and return their results.

        Returns:
            List of ValidationResult from each registered validator.

        """
        return [validator.validate() for validator in self.validators]

    def is_valid(self) -> bool:
        """Return True only if all validators pass.

        Returns:
            True if every registered validator passes, False otherwise.

        """
        return all(result.passed for result in self.validate_all())
