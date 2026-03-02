"""Tests for Library of Sense reasoning components."""

from __future__ import annotations

import pytest

from thalos_prime.library_of_sense.core.interfaces import QueryContext
from thalos_prime.library_of_sense.reasoning.constraint_solver import (
    ConstraintProblem,
    ConstraintSolver,
)
from thalos_prime.library_of_sense.reasoning.proof_checker import ProofChecker
from thalos_prime.library_of_sense.reasoning.symbolic_engine import SymbolicReasoningEngine

# ---------------------------------------------------------------------------
# SymbolicReasoningEngine
# ---------------------------------------------------------------------------


class TestSymbolicReasoningEngine:
    def test_simplify_valid_expression(self) -> None:
        engine = SymbolicReasoningEngine()
        simplified, steps = engine.simplify_expression("x + x")
        assert "2" in simplified or "x" in simplified
        assert len(steps) >= 2

    def test_simplify_invalid_expression_raises(self) -> None:
        engine = SymbolicReasoningEngine()
        with pytest.raises(ValueError, match="Cannot parse"):
            engine.simplify_expression("@@@invalid@@@")

    def test_differentiate_valid(self) -> None:
        engine = SymbolicReasoningEngine()
        deriv, steps = engine.differentiate("x**2", "x")
        assert "2" in deriv
        assert len(steps) >= 2

    def test_differentiate_invalid_raises(self) -> None:
        engine = SymbolicReasoningEngine()
        with pytest.raises(ValueError, match="Cannot differentiate"):
            engine.differentiate("@@@", "x")

    def test_reason_valid_expression(self) -> None:
        engine = SymbolicReasoningEngine()
        ctx = QueryContext()
        result = engine.reason("x + x", ctx)
        assert result.valid is True
        assert result.confidence > 0

    def test_reason_invalid_expression(self) -> None:
        engine = SymbolicReasoningEngine()
        ctx = QueryContext()
        result = engine.reason("@@@invalid@@@", ctx)
        assert result.valid is False
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# ProofChecker
# ---------------------------------------------------------------------------


class TestProofChecker:
    def test_check_equivalence_equal(self) -> None:
        checker = ProofChecker()
        result = checker.check_equivalence("x + x", "2*x")
        assert result.valid is True

    def test_check_equivalence_not_equal(self) -> None:
        checker = ProofChecker()
        result = checker.check_equivalence("x + 1", "2*x")
        assert result.valid is False

    def test_check_equivalence_invalid_expression(self) -> None:
        checker = ProofChecker()
        result = checker.check_equivalence("@@@", "x")
        assert result.valid is False

    def test_check_identity_zero(self) -> None:
        checker = ProofChecker()
        result = checker.check_identity("(x + y) - x - y")
        assert result.valid is True

    def test_check_identity_not_zero(self) -> None:
        checker = ProofChecker()
        result = checker.check_identity("x + 1")
        assert result.valid is False


# ---------------------------------------------------------------------------
# ConstraintSolver
# ---------------------------------------------------------------------------


class TestConstraintSolver:
    def test_solve_satisfiable(self) -> None:
        solver = ConstraintSolver()
        problem = ConstraintProblem(
            int_vars=["x", "y"],
            constraints=["x > 0", "y > 0", "x + y == 5"],
        )
        result = solver.solve(problem)
        assert result.status == "sat"

    def test_solve_unsatisfiable(self) -> None:
        solver = ConstraintSolver()
        problem = ConstraintProblem(
            int_vars=["x"],
            constraints=["x > 10", "x < 5"],
        )
        result = solver.solve(problem)
        assert result.status == "unsat"

    def test_check_satisfiable_valid(self) -> None:
        solver = ConstraintSolver()
        problem = ConstraintProblem(int_vars=["x"], constraints=["x > 0"])
        result = solver.check_satisfiable(problem)
        assert result.valid is True

    def test_check_satisfiable_invalid(self) -> None:
        solver = ConstraintSolver()
        problem = ConstraintProblem(int_vars=["x"], constraints=["x > 10", "x < 5"])
        result = solver.check_satisfiable(problem)
        assert result.valid is False
