"""Tests for registered, directive-gated workflow execution."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from thalos_prime.experiments import (
    ExperimentPlan,
    ExperimentSpec,
    HumanDirectiveRecord,
    MetricDefinition,
    MetricDirection,
    StageSpec,
    StageStatus,
    WorkflowExecutor,
    authorize_experiment_operation,
    default_research_plan,
)


def make_keypair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """Create an ephemeral RSA test key pair."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def make_directive(operations: list[str]) -> HumanDirectiveRecord:
    """Create and sign a task directive with an explicit allowlist."""
    private_key, _ = make_keypair()
    directive = HumanDirectiveRecord(
        directive_id="workflow-test-directive",
        timestamp=datetime(2026, 10, 22, tzinfo=timezone.utc),
        objectives=["Execute only registered research stages"],
        success_criteria=["Record stage results"],
        prohibited_operations=["deploy"],
        permitted_operations=operations,
    )
    directive.sign(private_key, "workflow-test-signer")
    return directive


def make_spec(directive: HumanDirectiveRecord) -> ExperimentSpec:
    """Bind the experiment spec to the current signed directive."""
    return ExperimentSpec(
        experiment_id="workflow-test-experiment",
        task_family="workflow-unit-test",
        task_description="Exercise dependency and permission controls",
        dataset_version="workflow-fixture-v1",
        baseline_candidate_id="baseline",
        primary_metric="pass_rate",
        metrics=[
            MetricDefinition(
                name="pass_rate",
                direction=MetricDirection.MAXIMIZE,
                target_value=0.8,
            )
        ],
        directive_id=directive.directive_id,
        directive_digest=directive.directive_digest,
    )


def test_default_plan_executes_only_registered_allowlisted_handlers() -> None:
    """The entire multi-representation workflow can run through trusted handlers."""
    plan = default_research_plan()
    operations = sorted({stage.operation for stage in plan.stages})
    private_key, public_key = make_keypair()
    directive = HumanDirectiveRecord(
        directive_id="full-plan-directive",
        timestamp=datetime(2026, 10, 22, tzinfo=timezone.utc),
        objectives=["Run each declarative research stage"],
        success_criteria=["All stages produce JSON-compatible results"],
        permitted_operations=operations,
    )
    directive.sign(private_key, "full-plan-reviewer")
    spec = make_spec(directive)

    executor = WorkflowExecutor()
    for operation in operations:
        executor.register(
            operation,
            lambda context: {
                "stage_id": context.stage_id,
                "dependency_ids": sorted(context.dependency_outputs),
                "goal": context.initial_context["goal"],
            },
        )

    report = executor.execute(
        plan=plan,
        spec=spec,
        directive=directive,
        public_key=public_key,
        initial_context={"goal": "compare representations"},
    )
    assert report.succeeded_count == len(plan.stages)
    assert report.failed_count == 0
    assert report.blocked_count == 0
    assert report.authorization_denied_count == 0
    assert report.timed_out_count == 0
    assert all(stage.output_digest is not None for stage in report.stages)
    assert len(report.report_digest) == 64


def test_unallowlisted_operation_is_denied_and_descendants_are_blocked() -> None:
    """Operation names from a plan cannot bypass the directive allowlist."""
    plan = ExperimentPlan(
        plan_id="deny-test",
        stages=[
            StageSpec(stage_id="safe-stage", operation="safe"),
            StageSpec(stage_id="restricted-stage", operation="restricted", depends_on=["safe-stage"]),
            StageSpec(stage_id="dependent-stage", operation="safe", depends_on=["restricted-stage"]),
        ],
    )
    private_key, public_key = make_keypair()
    directive = HumanDirectiveRecord(
        directive_id="deny-test-directive",
        timestamp=datetime(2026, 10, 22, tzinfo=timezone.utc),
        objectives=["Deny unauthorized stage operations"],
        success_criteria=["Unauthorized stage does not run"],
        permitted_operations=["safe"],
    )
    directive.sign(private_key, "reviewer")
    executor = WorkflowExecutor()
    invoked: list[str] = []
    executor.register("safe", lambda context: invoked.append(context.stage_id) or {"ok": True})
    executor.register("restricted", lambda context: invoked.append(context.stage_id) or {"ok": True})

    report = executor.execute(
        plan=plan,
        spec=make_spec(directive),
        directive=directive,
        public_key=public_key,
        initial_context={},
    )
    statuses = {stage.stage_id: stage.status for stage in report.stages}
    assert statuses["safe-stage"] is StageStatus.SUCCEEDED
    assert statuses["restricted-stage"] is StageStatus.UNAUTHORIZED
    assert statuses["dependent-stage"] is StageStatus.BLOCKED
    assert invoked == ["safe-stage"]
    assert report.authorization_denied_count == 1
    assert report.blocked_count == 1


def test_approval_gate_blocks_stage_without_explicit_approval() -> None:
    """A valid signature and allowlist do not substitute for stage approval."""
    plan = ExperimentPlan(
        plan_id="approval-test",
        stages=[
            StageSpec(
                stage_id="review",
                operation="review",
                requires_approval=True,
            )
        ],
    )
    private_key, public_key = make_keypair()
    directive = HumanDirectiveRecord(
        directive_id="approval-directive",
        timestamp=datetime(2026, 10, 22, tzinfo=timezone.utc),
        objectives=["Require a separate approval gate"],
        success_criteria=["No stage executes without approval"],
        permitted_operations=["review"],
    )
    directive.sign(private_key, "reviewer")
    executor = WorkflowExecutor()
    invoked: list[str] = []
    executor.register("review", lambda context: invoked.append("review") or {"ok": True})

    report = executor.execute(
        plan=plan,
        spec=make_spec(directive),
        directive=directive,
        public_key=public_key,
        initial_context={},
    )
    assert report.approval_required_count == 1
    assert report.stages[0].status is StageStatus.APPROVAL_REQUIRED
    assert invoked == []

    approved_report = executor.execute(
        plan=plan,
        spec=make_spec(directive),
        directive=directive,
        public_key=public_key,
        initial_context={},
        approved_stage_ids={"review"},
    )
    assert approved_report.stages[0].status is StageStatus.SUCCEEDED
    assert invoked == ["review"]


def test_failed_branch_does_not_stop_an_independent_branch() -> None:
    """Only descendants of failed stages are blocked."""
    plan = ExperimentPlan(
        plan_id="branch-failure-test",
        stages=[
            StageSpec(stage_id="root", operation="root"),
            StageSpec(stage_id="left", operation="left", depends_on=["root"]),
            StageSpec(stage_id="right", operation="right", depends_on=["root"]),
            StageSpec(
                stage_id="join",
                operation="join",
                depends_on=["left", "right"],
            ),
        ],
    )
    private_key, public_key = make_keypair()
    directive = HumanDirectiveRecord(
        directive_id="branch-failure-directive",
        timestamp=datetime(2026, 10, 22, tzinfo=timezone.utc),
        objectives=["Preserve independent branch outcomes"],
        success_criteria=["Successful independent work is retained"],
        permitted_operations=["root", "left", "right", "join"],
    )
    directive.sign(private_key, "reviewer")
    executor = WorkflowExecutor()
    executor.register("root", lambda context: {"root": True})

    def fail_left(context: object) -> dict[str, object]:
        """Represent a stage handler that failed."""
        raise RuntimeError("controlled failure")

    executor.register("left", fail_left)
    executor.register("right", lambda context: {"right": True})
    executor.register("join", lambda context: {"joined": True})

    report = executor.execute(
        plan=plan,
        spec=make_spec(directive),
        directive=directive,
        public_key=public_key,
        initial_context={},
    )
    statuses = {stage.stage_id: stage.status for stage in report.stages}
    assert statuses["root"] is StageStatus.SUCCEEDED
    assert statuses["left"] is StageStatus.FAILED
    assert statuses["right"] is StageStatus.SUCCEEDED
    assert statuses["join"] is StageStatus.BLOCKED
    failed = next(stage for stage in report.stages if stage.stage_id == "left")
    assert failed.error_type == "RuntimeError"
    assert failed.error_message == "controlled failure"


def test_unregistered_handler_fails_explicitly() -> None:
    """A declarative operation is not dynamically imported or executed."""
    plan = ExperimentPlan(
        plan_id="missing-handler-test",
        stages=[StageSpec(stage_id="missing", operation="not-registered")],
    )
    private_key, public_key = make_keypair()
    directive = HumanDirectiveRecord(
        directive_id="missing-handler-directive",
        timestamp=datetime(2026, 10, 22, tzinfo=timezone.utc),
        objectives=["Fail closed on unregistered operations"],
        success_criteria=["No dynamic import occurs"],
        permitted_operations=["not-registered"],
    )
    directive.sign(private_key, "reviewer")
    report = WorkflowExecutor().execute(
        plan=plan,
        spec=make_spec(directive),
        directive=directive,
        public_key=public_key,
        initial_context={},
    )
    assert report.failed_count == 1
    assert report.stages[0].error_type == "HandlerNotRegistered"


def test_handler_output_must_be_bounded_json() -> None:
    """Oversized outputs are failed and cannot feed dependent stages."""
    plan = ExperimentPlan(
        plan_id="output-limit-test",
        stages=[StageSpec(stage_id="large", operation="large")],
    )
    private_key, public_key = make_keypair()
    directive = HumanDirectiveRecord(
        directive_id="output-limit-directive",
        timestamp=datetime(2026, 10, 22, tzinfo=timezone.utc),
        objectives=["Bound handler outputs"],
        success_criteria=["Large outputs are rejected"],
        permitted_operations=["large"],
    )
    directive.sign(private_key, "reviewer")
    executor = WorkflowExecutor(max_stage_output_bytes=64)
    executor.register("large", lambda context: {"payload": "x" * 1000})
    report = executor.execute(
        plan=plan,
        spec=make_spec(directive),
        directive=directive,
        public_key=public_key,
        initial_context={},
    )
    assert report.failed_count == 1
    assert report.stages[0].error_type == "ValueError"
    assert "exceeds 64 bytes" in (report.stages[0].error_message or "")


def test_directive_mismatch_fails_before_any_handler_runs() -> None:
    """A different signed task cannot authorize the supplied experiment spec."""
    plan = ExperimentPlan(
        plan_id="directive-mismatch",
        stages=[StageSpec(stage_id="stage", operation="safe")],
    )
    private_key, public_key = make_keypair()
    directive = HumanDirectiveRecord(
        directive_id="correct-directive",
        timestamp=datetime(2026, 10, 22, tzinfo=timezone.utc),
        objectives=["Check directive binding"],
        success_criteria=["Reject mismatch"],
        permitted_operations=["safe"],
    )
    directive.sign(private_key, "reviewer")
    spec = ExperimentSpec(
        experiment_id="mismatch",
        task_family="test",
        task_description="A mismatched directive",
        dataset_version="v1",
        baseline_candidate_id="baseline",
        primary_metric="pass_rate",
        metrics=[MetricDefinition(name="pass_rate", direction=MetricDirection.MAXIMIZE)],
        directive_id="different-directive",
        directive_digest=directive.directive_digest,
    )
    executor = WorkflowExecutor()
    executor.register("safe", lambda context: {"executed": True})
    with pytest.raises(PermissionError, match="ID does not match"):
        executor.execute(
            plan=plan,
            spec=spec,
            directive=directive,
            public_key=public_key,
            initial_context={},
        )


def test_handler_context_changes_do_not_mutate_prior_outputs() -> None:
    """The executor gives handlers JSON-cloned inputs, not stored output objects."""
    plan = ExperimentPlan(
        plan_id="input-copy-test",
        stages=[
            StageSpec(stage_id="first", operation="first"),
            StageSpec(stage_id="second", operation="second", depends_on=["first"]),
        ],
    )
    private_key, public_key = make_keypair()
    directive = HumanDirectiveRecord(
        directive_id="input-copy-directive",
        timestamp=datetime(2026, 10, 22, tzinfo=timezone.utc),
        objectives=["Prevent cross-stage mutation"],
        success_criteria=["Dependency output remains intact"],
        permitted_operations=["first", "second"],
    )
    directive.sign(private_key, "reviewer")
    executor = WorkflowExecutor()
    executor.register("first", lambda context: {"nested": {"value": 1}})

    def mutate_dependency(context: object) -> dict[str, object]:
        """Try to alter one handler's dependency copy."""
        stage_context = context
        stage_context.dependency_outputs["first"]["nested"]["value"] = 99  # type: ignore[attr-defined]
        return {"observed": stage_context.dependency_outputs["first"]["nested"]["value"]}

    executor.register("second", mutate_dependency)
    report = executor.execute(
        plan=plan,
        spec=make_spec(directive),
        directive=directive,
        public_key=public_key,
        initial_context={},
    )
    assert [stage.status for stage in report.stages] == [
        StageStatus.SUCCEEDED,
        StageStatus.SUCCEEDED,
    ]
