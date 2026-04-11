"""Tests for SymbolicConstraintEngine."""

from __future__ import annotations

from typing import Any, cast

import pytest

from thalos_prime.constraints.symbolic_engine import (
    ConstraintSet,
    OptimizationObjective,
    SymbolicConstraintEngine,
    SymbolicSolution,
    VariableDeclaration,
    VariableSort,
)


def _make_engine() -> SymbolicConstraintEngine:
    engine = SymbolicConstraintEngine(seed=0)
    engine.initialize()
    return engine


class TestVariableDeclaration:
    def test_to_dict_basic(self) -> None:
        v = VariableDeclaration(name="x", sort=VariableSort.INT)
        d = v.to_dict()
        assert d["name"] == "x"
        assert d["sort"] == "int"

    def test_to_dict_with_bounds(self) -> None:
        v = VariableDeclaration(
            name="y", sort=VariableSort.REAL, lower_bound=0.0, upper_bound=10.0,
        )
        d = v.to_dict()
        assert d["lower_bound"] == 0.0
        assert d["upper_bound"] == 10.0


class TestConstraintSet:
    def test_to_dict(self) -> None:
        cs = ConstraintSet(
            name="test",
            variables=[VariableDeclaration(name="x", sort=VariableSort.INT)],
            constraints=["x > 0"],
        )
        d = cs.to_dict()
        assert d["name"] == "test"
        variables = cast(list[dict[str, Any]], d["variables"])
        constraints = cast(list[str], d["constraints"])
        assert len(variables) == 1
        assert constraints == ["x > 0"]


class TestSymbolicSolution:
    def test_to_dict_sat(self) -> None:
        s = SymbolicSolution(satisfiable=True, model={"x": "5"}, message="Satisfiable")
        d = s.to_dict()
        assert d["satisfiable"] is True
        model = cast(dict[str, str], d["model"])
        assert model["x"] == "5"

    def test_to_dict_with_objective(self) -> None:
        s = SymbolicSolution(
            satisfiable=True, model={"x": "3"}, objective_value="3", message="Optimal",
        )
        d = s.to_dict()
        assert d["objective_value"] == "3"


class TestSymbolicConstraintEngine:
    def test_initialize_sets_initialized(self) -> None:
        engine = _make_engine()
        assert engine._initialized is True

    def test_validate_fails_before_initialize(self) -> None:
        engine = SymbolicConstraintEngine()
        result = engine.validate()
        assert result.valid is False

    def test_validate_passes_after_initialize(self) -> None:
        engine = _make_engine()
        result = engine.validate()
        assert result.valid is True

    def test_solve_simple_sat(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="simple",
            variables=[VariableDeclaration(name="x", sort=VariableSort.INT)],
            constraints=["x > 0", "x < 10"],
        )
        result = engine.solve(cs)
        assert result.satisfiable is True
        assert "x" in result.model
        x_val = int(result.model["x"])
        assert 0 < x_val < 10

    def test_solve_unsat(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="unsat",
            variables=[VariableDeclaration(name="x", sort=VariableSort.INT)],
            constraints=["x > 10", "x < 5"],
        )
        result = engine.solve(cs)
        assert result.satisfiable is False

    def test_solve_with_bounds(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="bounded",
            variables=[
                VariableDeclaration(
                    name="x", sort=VariableSort.INT, lower_bound=1, upper_bound=5,
                ),
            ],
            constraints=["x > 3"],
        )
        result = engine.solve(cs)
        assert result.satisfiable is True
        x_val = int(result.model["x"])
        assert 3 < x_val <= 5

    def test_solve_real_vars(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="reals",
            variables=[VariableDeclaration(name="y", sort=VariableSort.REAL)],
            constraints=["y > 0", "y < 1"],
        )
        result = engine.solve(cs)
        assert result.satisfiable is True
        assert "y" in result.model

    def test_solve_bool_vars(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="bools",
            variables=[
                VariableDeclaration(name="a", sort=VariableSort.BOOL),
                VariableDeclaration(name="b", sort=VariableSort.BOOL),
            ],
            constraints=["a != b"],
        )
        result = engine.solve(cs)
        assert result.satisfiable is True

    def test_solve_multi_variable(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="multi",
            variables=[
                VariableDeclaration(name="x", sort=VariableSort.INT),
                VariableDeclaration(name="y", sort=VariableSort.INT),
            ],
            constraints=["x + y == 10", "x > 3", "y > 3"],
        )
        result = engine.solve(cs)
        assert result.satisfiable is True
        x_val = int(result.model["x"])
        y_val = int(result.model["y"])
        assert x_val + y_val == 10

    def test_solve_unsafe_constraint_rejected(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="unsafe",
            variables=[VariableDeclaration(name="x", sort=VariableSort.INT)],
            constraints=["__import__('os')"],
        )
        result = engine.solve(cs)
        assert result.satisfiable is False

    def test_optimize_minimize(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="min",
            variables=[
                VariableDeclaration(
                    name="x", sort=VariableSort.INT, lower_bound=0, upper_bound=100,
                ),
            ],
            constraints=["x >= 5"],
        )
        obj = OptimizationObjective(expression="x", direction="minimize")
        result = engine.optimize(cs, obj)
        assert result.satisfiable is True
        assert result.objective_value is not None
        assert int(result.model["x"]) == 5

    def test_optimize_maximize(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="max",
            variables=[
                VariableDeclaration(
                    name="x", sort=VariableSort.INT, lower_bound=0, upper_bound=10,
                ),
            ],
            constraints=["x <= 7"],
        )
        obj = OptimizationObjective(expression="x", direction="maximize")
        result = engine.optimize(cs, obj)
        assert result.satisfiable is True
        assert int(result.model["x"]) == 7

    def test_register_and_solve(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="registered",
            variables=[VariableDeclaration(name="x", sort=VariableSort.INT)],
            constraints=["x == 42"],
        )
        engine.register_constraint_set(cs)
        assert "registered" in engine.registered_sets
        result = engine.solve_registered("registered")
        assert result.satisfiable is True
        assert result.model["x"] == "42"

    def test_solve_registered_missing_raises(self) -> None:
        engine = _make_engine()
        with pytest.raises(KeyError, match="No constraint set"):
            engine.solve_registered("nonexistent")

    def test_check_satisfiable(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="check",
            variables=[VariableDeclaration(name="x", sort=VariableSort.INT)],
            constraints=["x == 1"],
        )
        vr = engine.check_satisfiable(cs)
        assert vr.valid is True

    def test_solve_count_increments(self) -> None:
        engine = _make_engine()
        assert engine.solve_count == 0
        cs = ConstraintSet(
            name="count",
            variables=[VariableDeclaration(name="x", sort=VariableSort.INT)],
            constraints=["x == 1"],
        )
        engine.solve(cs)
        engine.solve(cs)
        assert engine.solve_count == 2

    def test_operate_does_not_raise(self) -> None:
        engine = _make_engine()
        engine.operate()

    def test_reconcile_fixes_negative(self) -> None:
        engine = _make_engine()
        engine._solve_count = -3
        engine.reconcile()
        assert engine._solve_count == 0

    def test_checkpoint_returns_dict(self) -> None:
        engine = _make_engine()
        state = engine.checkpoint()
        assert isinstance(state, dict)
        assert state["component"] == "SymbolicConstraintEngine"

    def test_terminate_resets_state(self) -> None:
        engine = _make_engine()
        cs = ConstraintSet(
            name="t",
            variables=[VariableDeclaration(name="x", sort=VariableSort.INT)],
            constraints=["x == 1"],
        )
        engine.register_constraint_set(cs)
        engine.solve(cs)
        engine.terminate()
        assert engine._initialized is False
        assert engine.solve_count == 0
        assert engine.registered_sets == []

    def test_lifecycle_events_recorded(self) -> None:
        engine = _make_engine()
        engine.operate()
        engine.checkpoint()
        engine.terminate()
        events = engine.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "operate" in methods
        assert "checkpoint" in methods
        assert "terminate" in methods
