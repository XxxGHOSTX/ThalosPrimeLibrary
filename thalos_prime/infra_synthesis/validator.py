"""Schema validator for infra-synthesis.

Data Plane helper: validates required sections and basic field constraints.
Validation is deterministic and produces a list of human-readable violations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_REQUIRED_SECTIONS = ("project", "compute", "network", "storage", "ci")

_VALID_COMPUTE_TYPES = frozenset({"container", "serverless", "vm"})
_VALID_NETWORK_PROTOCOLS = frozenset({"https", "http", "grpc", "tcp"})


@dataclass
class ValidationResult:
    """Result of schema validation.

    Attributes:
        valid: True only when there are no violations.
        violations: Human-readable list of constraint failures.

    """

    valid: bool
    violations: list[str] = field(default_factory=list)


class SchemaValidator:
    """Validates an infrastructure schema dict against required section rules.

    Implements the six-method lifecycle contract for participation in
    lifecycle-managed pipelines.

    Checks that all top-level required sections exist and that their fields
    satisfy basic constraints.  No default substitution is performed — missing
    fields are reported as violations.
    """

    def __init__(self) -> None:
        """Initialize the schema validator."""
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle contract
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Mark the validator as initialized."""
        self._initialized = True
        logger.debug("SchemaValidator: initialized")

    def operate(self) -> None:
        """Log current operational status (idempotent)."""
        logger.debug("SchemaValidator: operating, initialized=%s", self._initialized)

    def reconcile(self) -> None:
        """No-op reconcile; SchemaValidator holds no mutable state."""
        logger.debug("SchemaValidator: reconciled")

    def checkpoint(self) -> dict[str, Any]:
        """Return a serializable snapshot of this validator's state.

        Returns:
            Dict with ``component`` and ``initialized`` fields.

        """
        return {
            "component": "SchemaValidator",
            "initialized": self._initialized,
        }

    def terminate(self) -> None:
        """Mark the validator as uninitialized."""
        self._initialized = False
        logger.debug("SchemaValidator: terminated")

    # ------------------------------------------------------------------
    # Domain operations
    # ------------------------------------------------------------------

    def validate(self, schema: dict[str, Any]) -> ValidationResult:
        """Validate *schema* and return a :class:`ValidationResult`.

        Args:
            schema: Parsed schema dict (output of :class:`SchemaLoader`).

        Returns:
            ValidationResult with ``valid=True`` when no violations are found.

        """
        violations: list[str] = [
            f"Missing required section: '{section}'"
            for section in _REQUIRED_SECTIONS
            if section not in schema
        ]

        if violations:
            return ValidationResult(valid=False, violations=violations)

        self._validate_project(schema["project"], violations)
        self._validate_compute(schema["compute"], violations)
        self._validate_network(schema["network"], violations)
        self._validate_storage(schema["storage"], violations)
        self._validate_ci(schema["ci"], violations)

        is_valid = len(violations) == 0
        if is_valid:
            logger.debug("Schema validation passed")
        else:
            for v in violations:
                logger.warning("Schema violation: %s", v)

        return ValidationResult(valid=is_valid, violations=violations)

    def _validate_project(self, section: object, violations: list[str]) -> None:
        if not isinstance(section, dict):
            violations.append("'project' must be a mapping")
            return
        violations.extend(
            f"'project.{key}' is required and must be non-empty"
            for key in ("name", "version")
            if not section.get(key)
        )

    def _validate_compute(self, section: object, violations: list[str]) -> None:
        if not isinstance(section, dict):
            violations.append("'compute' must be a mapping")
            return
        compute_type = section.get("type")
        if not compute_type:
            violations.append("'compute.type' is required")
        elif compute_type not in _VALID_COMPUTE_TYPES:
            violations.append(
                f"'compute.type' must be one of {sorted(_VALID_COMPUTE_TYPES)}; "
                f"got '{compute_type}'"
            )
        scaling = section.get("scaling")
        if scaling is not None and (not isinstance(scaling, int) or scaling < 1):
            violations.append("'compute.scaling' must be a positive integer")

    def _validate_network(self, section: object, violations: list[str]) -> None:
        if not isinstance(section, dict):
            violations.append("'network' must be a mapping")
            return
        protocol = section.get("protocol")
        if not protocol:
            violations.append("'network.protocol' is required")
        elif protocol not in _VALID_NETWORK_PROTOCOLS:
            violations.append(
                f"'network.protocol' must be one of {sorted(_VALID_NETWORK_PROTOCOLS)}; "
                f"got '{protocol}'"
            )

    def _validate_storage(self, section: object, violations: list[str]) -> None:
        if not isinstance(section, dict):
            violations.append("'storage' must be a mapping")
            return
        if "backend" not in section:
            violations.append("'storage.backend' is required")

    def _validate_ci(self, section: object, violations: list[str]) -> None:
        if not isinstance(section, dict):
            violations.append("'ci' must be a mapping")
            return
        if "provider" not in section:
            violations.append("'ci.provider' is required")


__all__ = ["SchemaValidator", "ValidationResult"]
