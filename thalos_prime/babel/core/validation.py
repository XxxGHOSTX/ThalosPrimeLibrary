"""Validation utilities for Babel subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ValidationResult:
    """Result of a single validation check."""

    passed: bool
    message: str
    details: dict[str, Any]


class Validator(Protocol):
    """Protocol for validators."""

    def validate(self) -> ValidationResult:
        """Run validation and return result."""
        ...


class SystemValidator:
    """Run registered validators and aggregate results."""

    def __init__(self) -> None:
        """Initialize with empty validator list."""
        self.validators: list[Validator] = []

    def register(self, validator: Validator) -> None:
        """Register a validator."""
        self.validators.append(validator)

    def validate_all(self) -> list[ValidationResult]:
        """Run all validators and return results."""
        return [validator.validate() for validator in self.validators]

    def is_valid(self) -> bool:
        """Return True if all validators pass."""
        return all(result.passed for result in self.validate_all())
