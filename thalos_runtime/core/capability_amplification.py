"""Capability amplification kernel.

The kernel is deliberately narrow: it selects a registered capability provider,
executes one bounded operation, independently validates the result, and may
fail over only to a different provider. Multi-step composition belongs to
ExecutionGraph; lifecycle state remains in the Control Plane.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Capability(StrEnum):
    """Atomic capability labels used for deterministic routing."""

    REASON = "reason"
    RETRIEVE = "retrieve"
    INSPECT = "inspect"
    CALCULATE = "calculate"
    EXECUTE = "execute"
    VALIDATE = "validate"
    COMPARE = "compare"
    TRANSFORM = "transform"


class AmplificationStatus(StrEnum):
    """Terminal task outcomes."""

    COMPLETED_VERIFIED = "completed_verified"
    COMPLETED_QUALIFIED = "completed_qualified"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    HALTED = "halted"


class FailureCode(StrEnum):
    """Machine-readable failure classes used by the corrective loop."""

    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    EXECUTION_FAILED = "execution_failed"
    VALIDATION_UNAVAILABLE = "validation_unavailable"
    VALIDATION_FAILED = "validation_failed"
    OUTPUT_INVALID = "output_invalid"
    POLICY_VIOLATION = "policy_violation"


class TaskContract(BaseModel):
    """Minimal executable contract for one bounded operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(default="2.0.0", pattern=r"^2\.0\.0$")
    task_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    required_capabilities: tuple[Capability, ...] = Field(min_length=1)
    acceptance_criteria: tuple[str, ...] = Field(min_length=1)
    max_attempts: int = Field(default=2, ge=1, le=8)
    allow_failover: bool = True


class ValidationCheck(BaseModel):
    """One independently executed validation check."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    validator: str = Field(min_length=1)
    passed: bool
    blocking: bool = True
    detail: str = ""


class ValidationReport(BaseModel):
    """Aggregate validation result for one provider output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    checks: tuple[ValidationCheck, ...]
    passed: bool
    blocking_failure: bool = False


class OperationRecord(BaseModel):
    """Immutable record for one provider attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str
    attempt: int = Field(ge=1)
    provider_id: str
    input_hash: str
    output_hash: str | None = None
    status: str
    failure: FailureCode | None = None


class AmplificationResult(BaseModel):
    """Canonical result envelope emitted by the amplification kernel."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result_id: str
    task_id: str
    status: AmplificationStatus
    provider_id: str | None = None
    output: Any = None
    attempts: tuple[OperationRecord, ...] = ()
    validation: ValidationReport | None = None
    failures: tuple[FailureCode, ...] = ()
    provenance: dict[str, Any] = Field(default_factory=dict)
    replayable: bool = True


class CapabilityProvider(Protocol):
    """Provider contract for a concrete capability implementation."""

    @property
    def provider_id(self) -> str:
        """Return the stable provider identifier."""
        ...

    @property
    def capabilities(self) -> frozenset[Capability]:
        """Return the atomic capabilities implemented by this provider."""
        ...

    def execute(self, payload: dict[str, Any]) -> Any:
        """Execute the bounded operation."""
        ...


@dataclass(frozen=True)
class CallableCapabilityProvider:
    """Adapter for an ordinary deterministic callable."""

    provider_id: str
    capabilities: frozenset[Capability]
    operation: Callable[[dict[str, Any]], Any]

    def execute(self, payload: dict[str, Any]) -> Any:
        """Execute the wrapped callable."""
        return self.operation(payload)


class CapabilityValidator(Protocol):
    """Independent validator contract."""

    @property
    def validator_id(self) -> str:
        """Return a stable validator identifier."""
        ...

    def validate(
        self,
        contract: TaskContract,
        output: Any,
    ) -> ValidationCheck:
        """Validate the provider output against the task contract."""
        ...


@dataclass(frozen=True)
class NonEmptyValidator:
    """Validator that rejects empty provider output."""

    validator_id: str = "non_empty"

    def validate(
        self,
        contract: TaskContract,
        output: Any,
    ) -> ValidationCheck:
        """Return a passing check when output is materially non-empty."""
        if output is None:
            return ValidationCheck(
                validator=self.validator_id,
                passed=False,
                detail="output is None",
            )
        if isinstance(output, str) and not output.strip():
            return ValidationCheck(
                validator=self.validator_id,
                passed=False,
                detail="output string is empty",
            )
        if isinstance(output, (Sequence, Mapping)) and len(output) == 0:
            return ValidationCheck(
                validator=self.validator_id,
                passed=False,
                detail="output collection is empty",
            )
        return ValidationCheck(
            validator=self.validator_id,
            passed=True,
            detail="output contains data",
        )


@dataclass(frozen=True)
class CallableValidator:
    """Adapter for a project-specific independent validator."""

    validator_id: str
    operation: Callable[[TaskContract, Any], ValidationCheck]

    def validate(
        self,
        contract: TaskContract,
        output: Any,
    ) -> ValidationCheck:
        """Execute the wrapped validator."""
        return self.operation(contract, output)


class CapabilityRouter:
    """Deterministic provider registry and selector."""

    def __init__(self) -> None:
        """Initialize an empty provider registry."""
        self._providers: dict[str, CapabilityProvider] = {}

    def register(self, provider: CapabilityProvider) -> None:
        """Register a unique provider."""
        if provider.provider_id in self._providers:
            raise ValueError(f"provider already registered: {provider.provider_id}")
        self._providers[provider.provider_id] = provider

    def candidates(self, required: frozenset[Capability]) -> list[CapabilityProvider]:
        """Return providers that satisfy every requested capability."""
        matches = [
            provider
            for provider in self._providers.values()
            if required.issubset(provider.capabilities)
        ]
        return sorted(matches, key=lambda provider: provider.provider_id)

    def provider_ids(self) -> list[str]:
        """Return registered provider IDs in deterministic order."""
        return sorted(self._providers)


class CapabilityAmplifier:
    """Narrow control-plane loop for capability amplification."""

    def __init__(
        self,
        router: CapabilityRouter,
        validators: Sequence[CapabilityValidator] | None = None,
    ) -> None:
        """Initialize the amplifier with routing and validation policy."""
        self._router = router
        self._validators = tuple(validators or (NonEmptyValidator(),))

    @staticmethod
    def _stable_hash(value: Any) -> str:
        """Hash JSON-compatible values deterministically."""
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json")
        elif hasattr(value, "to_dict"):
            value = value.to_dict()
        serialized = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def build_contract(
        cls,
        *,
        objective: str,
        payload: dict[str, Any],
        required_capabilities: Sequence[Capability],
        acceptance_criteria: Sequence[str],
        max_attempts: int = 2,
        allow_failover: bool = True,
    ) -> TaskContract:
        """Construct a deterministic contract ID from normalized inputs."""
        normalized = {
            "objective": " ".join(objective.split()),
            "payload": payload,
            "required_capabilities": sorted(str(c) for c in required_capabilities),
            "acceptance_criteria": list(acceptance_criteria),
            "max_attempts": max_attempts,
            "allow_failover": allow_failover,
        }
        task_id = f"task-{cls._stable_hash(normalized)[:24]}"
        return TaskContract(
            task_id=task_id,
            objective=normalized["objective"],
            payload=payload,
            required_capabilities=tuple(required_capabilities),
            acceptance_criteria=tuple(acceptance_criteria),
            max_attempts=max_attempts,
            allow_failover=allow_failover,
        )

    def run(self, contract: TaskContract) -> AmplificationResult:
        """Execute, validate, and terminate in an explicit terminal state."""
        try:
            contract = TaskContract.model_validate(contract)
        except ValidationError as exc:
            result_id = f"result-{self._stable_hash(str(exc))[:24]}"
            return AmplificationResult(
                result_id=result_id,
                task_id="invalid",
                status=AmplificationStatus.REJECTED,
                failures=(FailureCode.OUTPUT_INVALID,),
                provenance={"stage": "contract_validation"},
                replayable=True,
            )

        required = frozenset(contract.required_capabilities)
        candidates = self._router.candidates(required)
        input_hash = self._stable_hash(contract.payload)
        result_id = f"result-{self._stable_hash(contract.model_dump(mode="json"))[:24]}"

        if not candidates:
            return AmplificationResult(
                result_id=result_id,
                task_id=contract.task_id,
                status=AmplificationStatus.BLOCKED,
                failures=(FailureCode.CAPABILITY_UNAVAILABLE,),
                provenance={
                    "objective": contract.objective,
                    "required_capabilities": sorted(str(c) for c in required),
                    "input_hash": input_hash,
                },
                replayable=True,
            )

        records: list[OperationRecord] = []
        failures: list[FailureCode] = []
        selected_provider: str | None = None
        best_output: Any = None
        best_report: ValidationReport | None = None

        allowed_attempts = min(
            contract.max_attempts,
            len(candidates) if contract.allow_failover else 1,
        )

        for index in range(allowed_attempts):
            provider = candidates[index]
            selected_provider = provider.provider_id
            operation_id = (
                f"op-{self._stable_hash((contract.task_id, provider.provider_id, input_hash))[:24]}"
            )

            try:
                output = provider.execute(dict(contract.payload))
            except Exception:
                failures.append(FailureCode.EXECUTION_FAILED)
                records.append(
                    OperationRecord(
                        operation_id=operation_id,
                        attempt=index + 1,
                        provider_id=provider.provider_id,
                        input_hash=input_hash,
                        status="failed",
                        failure=FailureCode.EXECUTION_FAILED,
                    )
                )
                continue

            output_hash = self._stable_hash(output)
            checks = tuple(
                validator.validate(contract, output)
                for validator in self._validators
            )
            report = ValidationReport(
                checks=checks,
                passed=all(check.passed for check in checks),
                blocking_failure=any(
                    not check.passed and check.blocking for check in checks
                ),
            )
            best_output = output
            best_report = report

            records.append(
                OperationRecord(
                    operation_id=operation_id,
                    attempt=index + 1,
                    provider_id=provider.provider_id,
                    input_hash=input_hash,
                    output_hash=output_hash,
                    status="verified" if report.passed else "rejected",
                    failure=None if report.passed else FailureCode.VALIDATION_FAILED,
                )
            )

            if report.passed:
                return AmplificationResult(
                    result_id=result_id,
                    task_id=contract.task_id,
                    status=AmplificationStatus.COMPLETED_VERIFIED,
                    provider_id=provider.provider_id,
                    output=output,
                    attempts=tuple(records),
                    validation=report,
                    failures=tuple(failures),
                    provenance={
                        "objective": contract.objective,
                        "input_hash": input_hash,
                        "selected_provider": provider.provider_id,
                        "validator_ids": [
                            validator.validator_id for validator in self._validators
                        ],
                    },
                    replayable=True,
                )

            failures.append(FailureCode.VALIDATION_FAILED)

        if best_report is None and records:
            status = AmplificationStatus.HALTED
            terminal_failure = FailureCode.EXECUTION_FAILED
        elif best_report is not None and best_report.blocking_failure:
            status = AmplificationStatus.REJECTED
            terminal_failure = FailureCode.VALIDATION_FAILED
        else:
            status = AmplificationStatus.COMPLETED_QUALIFIED
            terminal_failure = None

        if terminal_failure is not None and terminal_failure not in failures:
            failures.append(terminal_failure)

        return AmplificationResult(
            result_id=result_id,
            task_id=contract.task_id,
            status=status,
            provider_id=selected_provider,
            output=best_output,
            attempts=tuple(records),
            validation=best_report,
            failures=tuple(failures),
            provenance={
                "objective": contract.objective,
                "input_hash": input_hash,
                "selected_provider": selected_provider,
                "validator_ids": [
                    validator.validator_id for validator in self._validators
                ],
            },
            replayable=True,
        )


__all__ = [
    "AmplificationResult",
    "AmplificationStatus",
    "Capability",
    "CapabilityAmplifier",
    "CapabilityProvider",
    "CapabilityRouter",
    "CapabilityValidator",
    "CallableCapabilityProvider",
    "CallableValidator",
    "FailureCode",
    "NonEmptyValidator",
    "OperationRecord",
    "TaskContract",
    "ValidationCheck",
    "ValidationReport",
]
