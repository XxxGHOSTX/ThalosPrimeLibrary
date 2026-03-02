"""
Validation utilities for Babel subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, List


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    message: str
    details: dict


class Validator(Protocol):
    def validate(self) -> ValidationResult:
        ...


class SystemValidator:
    """Run registered validators and aggregate results."""

    def __init__(self) -> None:
        self.validators: List[Validator] = []

    def register(self, validator: Validator) -> None:
        self.validators.append(validator)

    def validate_all(self) -> List[ValidationResult]:
        return [validator.validate() for validator in self.validators]

    def is_valid(self) -> bool:
        return all(result.passed for result in self.validate_all())
