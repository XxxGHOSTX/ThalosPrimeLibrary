"""Tests for ReasoningControlPlane."""

from __future__ import annotations

import pytest

from thalos_prime.library_of_sense.reasoning.constraint_solver import ConstraintProblem
from thalos_prime.reasoning.engine import (
    ReasoningControlPlane,
    ReasoningRequest,
)


class TestReasoningControlPlane:
    def test_initialize_sets_initialized(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        assert cp._initialized is True

    def test_validate_fails_before_initialize(self) -> None:
        cp = ReasoningControlPlane()
        result = cp.validate()
        assert result.valid is False
        assert "not initialized" in result.message

    def test_validate_passes_after_initialize(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        result = cp.validate()
        assert result.valid is True

    def test_symbolic_reasoning(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        req = ReasoningRequest(premise="x + x", mode="symbolic")
        resp = cp.reason(req)
        assert resp.mode == "symbolic"
        assert resp.result is not None
        assert resp.result.valid is True
        assert "2*x" in resp.result.conclusion

    def test_proof_equivalence(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        req = ReasoningRequest(
            premise="",
            mode="proof",
            proof_lhs="x + x",
            proof_rhs="2*x",
        )
        resp = cp.reason(req)
        assert resp.mode == "proof"
        assert resp.validation is not None
        assert resp.validation.valid is True

    def test_proof_identity(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        req = ReasoningRequest(premise="x - x", mode="proof")
        resp = cp.reason(req)
        assert resp.mode == "proof"
        assert resp.validation is not None
        assert resp.validation.valid is True

    def test_constraint_solving(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        problem = ConstraintProblem(
            int_vars=["x", "y"],
            constraints=["x > 0", "y > 0", "x + y == 10"],
        )
        req = ReasoningRequest(
            premise="",
            mode="constraint",
            constraint_problem=problem,
        )
        resp = cp.reason(req)
        assert resp.mode == "constraint"
        assert resp.solver_result is not None
        assert resp.solver_result.status == "sat"

    def test_reason_raises_if_not_initialized(self) -> None:
        cp = ReasoningControlPlane()
        req = ReasoningRequest(premise="x + 1")
        with pytest.raises(RuntimeError, match="not initialized"):
            cp.reason(req)

    def test_request_count_increments(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        req = ReasoningRequest(premise="x + 1")
        cp.reason(req)
        cp.reason(req)
        assert cp._request_count == 2

    def test_operate_does_not_raise(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        cp.operate()

    def test_reconcile_fixes_negative_counters(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        cp._request_count = -1
        cp._error_count = -2
        cp.reconcile()
        assert cp._request_count == 0
        assert cp._error_count == 0

    def test_checkpoint_returns_dict(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        state = cp.checkpoint()
        assert isinstance(state, dict)
        assert state["component"] == "ReasoningControlPlane"
        assert "request_count" in state

    def test_terminate_resets_state(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        cp.reason(ReasoningRequest(premise="x"))
        cp.terminate()
        assert cp._initialized is False
        assert cp._request_count == 0

    def test_lifecycle_events_recorded(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        cp.operate()
        cp.checkpoint()
        cp.terminate()
        events = cp.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "checkpoint" in methods
        assert "terminate" in methods

    def test_steps_contain_audit_trail(self) -> None:
        cp = ReasoningControlPlane()
        cp.initialize()
        req = ReasoningRequest(premise="x + x", mode="symbolic")
        resp = cp.reason(req)
        assert len(resp.steps) > 1
        assert "Dispatching to symbolic engine" in resp.steps[0]

    def test_deterministic_results(self) -> None:
        cp = ReasoningControlPlane(seed=42)
        cp.initialize()
        req = ReasoningRequest(premise="x**2 + 2*x + 1", mode="symbolic")
        resp_a = cp.reason(req)
        resp_b = cp.reason(req)
        assert resp_a.result is not None
        assert resp_b.result is not None
        assert resp_a.result.conclusion == resp_b.result.conclusion
