"""Tests for ActionExecutor agency subsystem."""

from __future__ import annotations

import pytest

from thalos_prime.agency.action_executor import (
    ActionExecutionError,
    ActionExecutor,
    ActionResult,
)


def _echo_handler(params: dict[str, object]) -> ActionResult:
    """Simple handler that echoes params back in the output."""
    return ActionResult(action="echo", success=True, output=dict(params))


def _fail_handler(params: dict[str, object]) -> ActionResult:
    """Handler that always reports failure."""
    _ = params
    return ActionResult(action="fail", success=False, error="intentional failure")


def _raising_handler(params: dict[str, object]) -> ActionResult:
    """Handler that raises an exception."""
    _ = params
    msg = "boom"
    raise RuntimeError(msg)


class TestActionResult:
    def test_defaults(self) -> None:
        result = ActionResult(action="test", success=True)
        assert result.output == {}
        assert result.error == ""

    def test_to_dict(self) -> None:
        result = ActionResult(action="a", success=False, error="e")
        d = result.to_dict()
        assert d["action"] == "a"
        assert d["success"] is False
        assert d["error"] == "e"


class TestActionExecutor:
    def test_initialize_sets_initialized(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        assert executor._initialized is True

    def test_validate_fails_before_initialize(self) -> None:
        executor = ActionExecutor()
        result = executor.validate()
        assert result.valid is False
        assert "not initialized" in result.message

    def test_validate_passes_after_initialize(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        result = executor.validate()
        assert result.valid is True

    def test_register_action(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.register_action("echo", _echo_handler)
        assert "echo" in executor.registered_actions

    def test_register_duplicate_raises(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.register_action("echo", _echo_handler)
        with pytest.raises(ValueError, match="already registered"):
            executor.register_action("echo", _echo_handler)

    def test_unregister_action(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.register_action("echo", _echo_handler)
        assert executor.unregister_action("echo") is True
        assert "echo" not in executor.registered_actions

    def test_unregister_missing_returns_false(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        assert executor.unregister_action("nope") is False

    def test_execute_success(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.register_action("echo", _echo_handler)
        result = executor.execute("echo", {"x": 1})
        assert result.success is True
        assert result.output["x"] == 1

    def test_execute_unknown_action(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        result = executor.execute("unknown", {})
        assert result.success is False
        assert "Unknown action" in result.error

    def test_execute_handler_raises(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.register_action("boom", _raising_handler)
        with pytest.raises(ActionExecutionError) as exc_info:
            executor.execute("boom", {})
        assert exc_info.value.result.success is False
        assert "RuntimeError" in exc_info.value.result.error

    def test_safe_execute_handler_raises(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.register_action("boom", _raising_handler)
        result = executor.safe_execute("boom", {})
        assert result.success is False
        assert "RuntimeError" in result.error

    def test_execute_failure_handler(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.register_action("fail", _fail_handler)
        result = executor.execute("fail", {})
        assert result.success is False
        assert result.error == "intentional failure"

    def test_history_tracks_executions(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.register_action("echo", _echo_handler)
        executor.execute("echo", {"a": 1})
        executor.execute("echo", {"b": 2})
        history = executor.get_history()
        assert len(history) == 2

    def test_registered_actions_sorted(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.register_action("beta", _echo_handler)
        executor.register_action("alpha", _echo_handler)
        assert executor.registered_actions == ["alpha", "beta"]

    def test_operate_does_not_raise(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.operate()

    def test_reconcile_fixes_negative_counters(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor._execution_count = -2
        executor.reconcile()
        assert executor._execution_count == 0

    def test_checkpoint_returns_dict(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        state = executor.checkpoint()
        assert isinstance(state, dict)
        assert state["component"] == "ActionExecutor"
        assert "registered_actions" in state
        assert "execution_count" in state

    def test_terminate_resets_state(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.register_action("echo", _echo_handler)
        executor.execute("echo", {})
        executor.terminate()
        assert executor._initialized is False
        assert executor.registered_actions == []
        assert executor.get_history() == []

    def test_lifecycle_events_recorded(self) -> None:
        executor = ActionExecutor()
        executor.initialize()
        executor.operate()
        executor.checkpoint()
        executor.terminate()
        events = executor.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "checkpoint" in methods
        assert "terminate" in methods
