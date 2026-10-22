"""Permission-gated executor for registered ThalosPrime workflow operations.

This runtime invokes only application-registered handlers. It never imports
or evaluates operation names, model-generated code, repository files, or shell
commands from a task payload. Handlers are trusted application code and must
enforce any resource limits or process isolation required by their operation.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import BaseModel, ConfigDict, Field

from thalos_prime.experiments.contracts import ExperimentSpec
from thalos_prime.experiments.directive import (
    HumanDirectiveRecord,
    authorize_experiment_operation,
)
from thalos_prime.experiments.plan import ExperimentPlan, StageSpec


_MAX_INITIAL_CONTEXT_BYTES = 1_048_576
_MAX_STAGE_INPUT_BYTES = 2_097_152
_MAX_STAGE_OUTPUT_BYTES = 1_048_576
_MAX_TOTAL_WORKFLOW_OUTPUT_BYTES = 20 * 1_048_576
_MAX_ERROR_TEXT_LENGTH = 500
_MAX_PLAN_STAGES = 200


class StageStatus(StrEnum):
    """Final state recorded for one workflow stage."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNAUTHORIZED = "unauthorized"
    APPROVAL_REQUIRED = "approval_required"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True)
class StageContext:
    """Read-only-by-contract inputs passed to a registered handler.

    Handlers receive a fresh JSON round-trip copy of the initial context and
    their direct dependency outputs. Mutating those values cannot change the
    executor's stored outputs for already-completed stages.
    """

    stage_id: str
    operation: str
    initial_context: dict[str, Any]
    dependency_outputs: dict[str, dict[str, Any]]


StageHandler = Callable[[StageContext], Mapping[str, object]]


class WorkflowStageResult(BaseModel):
    """Bounded summary of one stage execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: str
    operation: str
    status: StageStatus
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    output_refs: list[str] = Field(default_factory=list, max_length=500)
    elapsed_ms: float = Field(ge=0, allow_inf_nan=False)
    error_type: str | None = None
    error_message: str | None = None


class WorkflowExecutionReport(BaseModel):
    """Report of a permission-checked run of a declarative workflow."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_id: str
    plan_version: str
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    directive_id: str
    directive_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    stages: list[WorkflowStageResult]
    succeeded_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    authorization_denied_count: int = Field(ge=0)
    approval_required_count: int = Field(ge=0)
    timed_out_count: int = Field(ge=0)
    report_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


def _canonical_json(value: object) -> bytes:
    """Encode JSON-compatible values with a stable serialization."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: object) -> str:
    """Hash the stable JSON encoding of a value."""
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _clone_json_mapping(value: Mapping[str, object], *, label: str) -> dict[str, Any]:
    """Validate, size-bound, and clone a JSON mapping."""
    try:
        encoded = _canonical_json(value)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError(f"{label} must contain finite JSON-compatible values") from error
    if len(encoded) > _MAX_INITIAL_CONTEXT_BYTES:
        raise ValueError(f"{label} exceeds {_MAX_INITIAL_CONTEXT_BYTES} bytes")
    cloned = json.loads(encoded)
    if not isinstance(cloned, dict):
        raise ValueError(f"{label} must encode as a JSON object")
    return cloned


class WorkflowExecutor:
    """Execute a declarative plan using explicitly registered trusted handlers.

    The executor is sequential and stable: stages are visited in the plan's
    deterministic topological order. Independent branches can succeed even if
    a different branch fails; a stage is blocked only when one of its direct
    dependencies did not succeed.

    Stage timeout is detected after a handler returns. Python cannot safely
    terminate an arbitrary running callable in-process, so registered
    handlers that invoke long-running work must enforce a real timeout at
    their own process/tool boundary. This executor is not a sandbox.
    """

    def __init__(
        self,
        *,
        max_stage_input_bytes: int = _MAX_STAGE_INPUT_BYTES,
        max_stage_output_bytes: int = _MAX_STAGE_OUTPUT_BYTES,
        max_total_workflow_output_bytes: int = _MAX_TOTAL_WORKFLOW_OUTPUT_BYTES,
    ) -> None:
        """Create a registry with explicit input, per-stage, and total output limits."""
        if max_stage_input_bytes < 1:
            raise ValueError("max_stage_input_bytes must be at least 1")
        if max_stage_output_bytes < 1:
            raise ValueError("max_stage_output_bytes must be at least 1")
        if max_total_workflow_output_bytes < 1:
            raise ValueError("max_total_workflow_output_bytes must be at least 1")
        self._max_stage_input_bytes = max_stage_input_bytes
        self._max_stage_output_bytes = max_stage_output_bytes
        self._max_total_workflow_output_bytes = max_total_workflow_output_bytes
        self._handlers: dict[str, StageHandler] = {}

    def register(self, operation: str, handler: StageHandler) -> None:
        """Register a trusted handler under one exact operation name."""
        normalized = operation.strip()
        if not normalized:
            raise ValueError("operation name must not be blank")
        if normalized in self._handlers:
            raise ValueError(f"operation {normalized!r} is already registered")
        self._handlers[normalized] = handler

    def registered_operations(self) -> list[str]:
        """Return registered operation names in stable lexical order."""
        return sorted(self._handlers)

    def execute(
        self,
        *,
        plan: ExperimentPlan,
        spec: ExperimentSpec,
        directive: HumanDirectiveRecord,
        public_key: rsa.RSAPublicKey,
        initial_context: Mapping[str, object],
        approved_stage_ids: set[str] | None = None,
    ) -> WorkflowExecutionReport:
        """Run registered handlers subject to directive, dependency, and approval gates."""
        if len(plan.stages) > _MAX_PLAN_STAGES:
            raise ValueError(f"plan exceeds {_MAX_PLAN_STAGES} stages")
        if spec.directive_id != directive.directive_id:
            raise PermissionError("experiment directive ID does not match the signed directive")
        if spec.directive_digest != directive.directive_digest:
            raise PermissionError("experiment directive digest does not match the signed directive")
        if not directive.verify(public_key):
            raise PermissionError("directive signature is missing or invalid")

        cloned_initial = _clone_json_mapping(initial_context, label="initial_context")
        initial_context_bytes = len(_canonical_json(cloned_initial))
        successful_output_sizes: dict[str, int] = {}
        total_workflow_output_bytes = 0
        approvals = approved_stage_ids or set()
        stage_specs = {stage.stage_id: stage for stage in plan.stages}
        unknown_approvals = approvals - set(stage_specs)
        if unknown_approvals:
            raise ValueError(
                "approved_stage_ids contains unknown stages: "
                + ", ".join(sorted(unknown_approvals))
            )

        plan_digest = _digest(plan.model_dump(mode="json"))
        successful_outputs: dict[str, dict[str, Any]] = {}
        stage_results: list[WorkflowStageResult] = []

        for stage_id in plan.topological_order():
            stage = stage_specs[stage_id]
            dependency_failures = [
                dependency
                for dependency in stage.depends_on
                if not any(
                    result.stage_id == dependency and result.status is StageStatus.SUCCEEDED
                    for result in stage_results
                )
            ]
            dependency_outputs = {
                dependency: successful_outputs[dependency]
                for dependency in stage.depends_on
                if dependency in successful_outputs
            }
            if dependency_failures:
                input_digest = _digest(
                    {
                        "initial_context_digest": _digest(cloned_initial),
                        "dependency_outputs": {
                            dependency: _digest(output)
                            for dependency, output in sorted(dependency_outputs.items())
                        },
                    }
                )
                stage_results.append(
                    WorkflowStageResult(
                        stage_id=stage.stage_id,
                        operation=stage.operation,
                        status=StageStatus.BLOCKED,
                        input_digest=input_digest,
                        elapsed_ms=0.0,
                        error_type="DependencyNotSuccessful",
                        error_message="Dependencies did not succeed: "
                        + ", ".join(sorted(dependency_failures)),
                    )
                )
                continue

            estimated_input_bytes = (
                initial_context_bytes
                + 64
                + sum(
                    successful_output_sizes[dependency] + len(dependency) + 32
                    for dependency in dependency_outputs
                )
            )
            if estimated_input_bytes > self._max_stage_input_bytes:
                input_digest = _digest(
                    {
                        "initial_context_digest": _digest(cloned_initial),
                        "dependency_output_digests": {
                            dependency: _digest(output)
                            for dependency, output in sorted(dependency_outputs.items())
                        },
                    }
                )
                stage_results.append(
                    WorkflowStageResult(
                        stage_id=stage.stage_id,
                        operation=stage.operation,
                        status=StageStatus.FAILED,
                        input_digest=input_digest,
                        elapsed_ms=0.0,
                        error_type="StageInputTooLarge",
                        error_message=(
                            f"stage input exceeds estimated limit of "
                            f"{self._max_stage_input_bytes} bytes"
                        ),
                    )
                )
                continue

            input_payload = {
                "initial_context": cloned_initial,
                "dependency_outputs": dependency_outputs,
            }
            encoded_input = _canonical_json(input_payload)
            if len(encoded_input) > self._max_stage_input_bytes:
                input_digest = hashlib.sha256(encoded_input).hexdigest()
                stage_results.append(
                    WorkflowStageResult(
                        stage_id=stage.stage_id,
                        operation=stage.operation,
                        status=StageStatus.FAILED,
                        input_digest=input_digest,
                        elapsed_ms=0.0,
                        error_type="StageInputTooLarge",
                        error_message=(
                            f"stage input exceeds {self._max_stage_input_bytes} bytes"
                        ),
                    )
                )
                continue
            input_digest = hashlib.sha256(encoded_input).hexdigest()

            if stage.requires_approval and stage.stage_id not in approvals:
                stage_results.append(
                    WorkflowStageResult(
                        stage_id=stage.stage_id,
                        operation=stage.operation,
                        status=StageStatus.APPROVAL_REQUIRED,
                        input_digest=input_digest,
                        elapsed_ms=0.0,
                        error_type="ApprovalRequired",
                        error_message="Stage requires explicit approval before execution",
                    )
                )
                continue

            try:
                authorize_experiment_operation(
                    spec,
                    directive,
                    stage.operation,
                    public_key,
                )
            except PermissionError as error:
                stage_results.append(
                    WorkflowStageResult(
                        stage_id=stage.stage_id,
                        operation=stage.operation,
                        status=StageStatus.UNAUTHORIZED,
                        input_digest=input_digest,
                        elapsed_ms=0.0,
                        error_type=type(error).__name__,
                        error_message=str(error)[:_MAX_ERROR_TEXT_LENGTH],
                    )
                )
                continue

            handler = self._handlers.get(stage.operation)
            if handler is None:
                stage_results.append(
                    WorkflowStageResult(
                        stage_id=stage.stage_id,
                        operation=stage.operation,
                        status=StageStatus.FAILED,
                        input_digest=input_digest,
                        elapsed_ms=0.0,
                        error_type="HandlerNotRegistered",
                        error_message=f"No trusted handler registered for {stage.operation!r}",
                    )
                )
                continue

            context = StageContext(
                stage_id=stage.stage_id,
                operation=stage.operation,
                initial_context=_clone_json_mapping(
                    cloned_initial,
                    label="handler initial_context",
                ),
                dependency_outputs={
                    dependency: _clone_json_mapping(
                        output,
                        label=f"handler dependency {dependency!r}",
                    )
                    for dependency, output in dependency_outputs.items()
                },
            )
            start = time.perf_counter()
            try:
                handler_output = handler(context)
                encoded_output = _canonical_json(dict(handler_output))
                if len(encoded_output) > self._max_stage_output_bytes:
                    raise ValueError(
                        f"stage output exceeds {self._max_stage_output_bytes} bytes"
                    )
                if (
                    total_workflow_output_bytes + len(encoded_output)
                    > self._max_total_workflow_output_bytes
                ):
                    raise ValueError(
                        "total workflow output exceeds "
                        f"{self._max_total_workflow_output_bytes} bytes"
                    )
                decoded_output = json.loads(encoded_output)
                if not isinstance(decoded_output, dict):
                    raise ValueError("stage handler must return a JSON object")
                raw_output_refs = decoded_output.get("_artifact_refs", [])
                if (
                    not isinstance(raw_output_refs, list)
                    or len(raw_output_refs) > 500
                    or any(not isinstance(reference, str) for reference in raw_output_refs)
                ):
                    raise ValueError(
                        "reserved _artifact_refs output must be a list of strings"
                    )
                output_refs = [reference.strip() for reference in raw_output_refs]
                if any(not reference for reference in output_refs):
                    raise ValueError("output artifact references must not be blank")
                if len(output_refs) != len(set(output_refs)):
                    raise ValueError("output artifact references must be unique")
                output_digest = hashlib.sha256(encoded_output).hexdigest()
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                if elapsed_ms > stage.timeout_seconds * 1000.0:
                    stage_results.append(
                        WorkflowStageResult(
                            stage_id=stage.stage_id,
                            operation=stage.operation,
                            status=StageStatus.TIMED_OUT,
                            input_digest=input_digest,
                            output_digest=output_digest,
                            output_refs=output_refs,
                            elapsed_ms=elapsed_ms,
                            error_type="StageTimeoutExceeded",
                            error_message=(
                                "Handler returned after the configured timeout; "
                                "the call was not forcibly interrupted"
                            ),
                        )
                    )
                    continue
                successful_outputs[stage.stage_id] = decoded_output
                successful_output_sizes[stage.stage_id] = len(encoded_output)
                total_workflow_output_bytes += len(encoded_output)
                stage_results.append(
                    WorkflowStageResult(
                        stage_id=stage.stage_id,
                        operation=stage.operation,
                        status=StageStatus.SUCCEEDED,
                        input_digest=input_digest,
                        output_digest=output_digest,
                        output_refs=output_refs,
                        elapsed_ms=elapsed_ms,
                    )
                )
            # Handler exceptions are captured as structured failures; other branches continue.
            except (
                ArithmeticError,
                AssertionError,
                AttributeError,
                ImportError,
                IndexError,
                KeyError,
                LookupError,
                NameError,
                NotImplementedError,
                OSError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as error:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                stage_results.append(
                    WorkflowStageResult(
                        stage_id=stage.stage_id,
                        operation=stage.operation,
                        status=StageStatus.FAILED,
                        input_digest=input_digest,
                        elapsed_ms=elapsed_ms,
                        error_type=type(error).__name__,
                        error_message=str(error)[:_MAX_ERROR_TEXT_LENGTH],
                    )
                )

        counts = {
            status: sum(result.status is status for result in stage_results)
            for status in StageStatus
        }
        report_body = {
            "plan_id": plan.plan_id,
            "plan_version": plan.version,
            "plan_digest": plan_digest,
            "directive_id": directive.directive_id,
            "directive_digest": directive.directive_digest,
            "stages": [result.model_dump(mode="json") for result in stage_results],
            "succeeded_count": counts[StageStatus.SUCCEEDED],
            "failed_count": counts[StageStatus.FAILED],
            "blocked_count": counts[StageStatus.BLOCKED],
            "authorization_denied_count": counts[StageStatus.UNAUTHORIZED],
            "approval_required_count": counts[StageStatus.APPROVAL_REQUIRED],
            "timed_out_count": counts[StageStatus.TIMED_OUT],
        }
        return WorkflowExecutionReport(
            **report_body,
            report_digest=_digest(report_body),
        )


__all__ = [
    "StageContext",
    "StageHandler",
    "StageStatus",
    "WorkflowExecutionReport",
    "WorkflowExecutor",
    "WorkflowStageResult",
]
