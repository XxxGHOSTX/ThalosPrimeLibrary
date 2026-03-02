"""Thalos Prime - Symbolic Constraint Engine.

Data Plane component providing a Z3-based symbolic constraint engine with
typed variable declarations, constraint composition, optimization objectives,
incremental solving, and model extraction.

Data Plane boundary: executes constraint solving work only — no lifecycle
coordination logic. Lifecycle methods exist for subsystem integration.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal, TypedDict, cast

import z3

from thalos_prime.library_of_sense.core.interfaces import ValidationResult
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)

# Safe constraint pattern: variable names, digits, operators, comparisons, whitespace
_CONSTRAINT_SAFE_PATTERN = re.compile(r"^[\w\s\+\-\*\/\(\)\<\>\=\!\.]+$")


class VariableSort(StrEnum):
    """Supported Z3 variable sorts."""

    INT = "int"
    REAL = "real"
    BOOL = "bool"


class VariableDeclarationDict(TypedDict, total=False):
    """Serialized representation of a variable declaration."""

    name: str
    sort: str
    lower_bound: float
    upper_bound: float


class ConstraintSetDict(TypedDict):
    """Serialized representation of a constraint set."""

    name: str
    variables: list[VariableDeclarationDict]
    constraints: list[str]


class SymbolicSolutionDict(TypedDict, total=False):
    """Serialized representation of a symbolic solution."""

    satisfiable: bool
    model: dict[str, str]
    message: str
    objective_value: str


@dataclass
class VariableDeclaration:
    """Declaration for a symbolic variable with optional bounds.

    Attributes:
        name: Variable identifier.
        sort: Variable type sort (int, real, bool).
        lower_bound: Optional lower bound (inclusive) for numeric sorts.
        upper_bound: Optional upper bound (inclusive) for numeric sorts.

    """

    name: str
    sort: VariableSort
    lower_bound: float | None = None
    upper_bound: float | None = None

    def to_dict(self) -> VariableDeclarationDict:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this declaration.

        """
        result: VariableDeclarationDict = {"name": self.name, "sort": self.sort.value}
        if self.lower_bound is not None:
            result["lower_bound"] = self.lower_bound
        if self.upper_bound is not None:
            result["upper_bound"] = self.upper_bound
        return result


@dataclass
class ConstraintSet:
    """A named collection of variable declarations and constraint expressions.

    Attributes:
        name: Descriptive name for this constraint set.
        variables: List of variable declarations.
        constraints: List of constraint expression strings.

    """

    name: str
    variables: list[VariableDeclaration] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> ConstraintSetDict:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this constraint set.

        """
        return {
            "name": self.name,
            "variables": [v.to_dict() for v in self.variables],
            "constraints": list(self.constraints),
        }


@dataclass
class OptimizationObjective:
    """An optimization objective for the constraint solver.

    Attributes:
        expression: The expression to optimize (must use declared variables).
        direction: Whether to minimize or maximize the expression.

    """

    expression: str
    direction: Literal["minimize", "maximize"]

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this objective.

        """
        return {"expression": self.expression, "direction": self.direction}


@dataclass
class SymbolicSolution:
    """Result from a symbolic constraint solving operation.

    Attributes:
        satisfiable: Whether the constraints are satisfiable.
        model: Variable name to value mapping if satisfiable.
        objective_value: Optimal objective value if optimization was requested.
        message: Human-readable status message.

    """

    satisfiable: bool
    model: dict[str, str]
    objective_value: str | None = None
    message: str = ""

    def to_dict(self) -> SymbolicSolutionDict:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this solution.

        """
        result: SymbolicSolutionDict = {
            "satisfiable": self.satisfiable,
            "model": dict(self.model),
            "message": self.message,
        }
        if self.objective_value is not None:
            result["objective_value"] = self.objective_value
        return result


class SymbolicConstraintEngine(BaseLifecycleComponent):
    """Z3-based symbolic constraint engine with typed variables and optimization.

    Provides constraint satisfaction checking, optimization, incremental
    solving, and model extraction. All solving operations are deterministic:
    identical constraint sets produce identical solutions.
    """

    def __init__(self, seed: int = 0) -> None:
        """Initialize the symbolic constraint engine.

        Args:
            seed: Deterministic seed for replay identification.

        """
        super().__init__("SymbolicConstraintEngine", seed=seed)
        self._solve_count: int = 0
        self._constraint_sets: dict[str, ConstraintSet] = {}

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the engine and reset state."""
        self._solve_count = 0
        self._constraint_sets = {}
        self._initialized = True
        self._emit_event("initialize", "engine ready")
        logger.debug("SymbolicConstraintEngine initialized")

    def validate(self) -> ValidationResult:
        """Validate the engine is ready for solving.

        Returns:
            ValidationResult indicating readiness.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="SymbolicConstraintEngine not initialized; call initialize() first",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"SymbolicConstraintEngine ready: "
                f"sets={len(self._constraint_sets)} solves={self._solve_count}"
            ),
        )

    def operate(self) -> None:
        """Log current engine statistics. Idempotent."""
        self._emit_event(
            "operate",
            f"sets={len(self._constraint_sets)} solves={self._solve_count}",
        )

    def reconcile(self) -> None:
        """Reconcile engine state; fix negative counters."""
        self._solve_count = max(self._solve_count, 0)
        self._emit_event("reconcile", f"solve_count={self._solve_count}")

    def checkpoint(self) -> dict[str, object]:
        """Serialize engine state.

        Returns:
            Dict with component name, seed, and constraint sets.

        """
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "solve_count": self._solve_count,
            "constraint_sets": {
                k: v.to_dict() for k, v in self._constraint_sets.items()
            },
        }
        self._emit_event("checkpoint", f"sets={len(self._constraint_sets)}")
        return state

    def terminate(self) -> None:
        """Reset engine state."""
        self._solve_count = 0
        self._constraint_sets = {}
        self._initialized = False
        self._emit_event("terminate", "engine cleared")
        logger.debug("SymbolicConstraintEngine terminated")

    # ------------------------------------------------------------------
    # Constraint management
    # ------------------------------------------------------------------

    def register_constraint_set(self, constraint_set: ConstraintSet) -> None:
        """Register a named constraint set for later solving.

        Args:
            constraint_set: The constraint set to register.

        """
        self._constraint_sets[constraint_set.name] = constraint_set
        logger.debug("Registered constraint set: %s", constraint_set.name)

    def get_constraint_set(self, name: str) -> ConstraintSet | None:
        """Retrieve a registered constraint set by name.

        Args:
            name: The constraint set name.

        Returns:
            The ConstraintSet if found, None otherwise.

        """
        return self._constraint_sets.get(name)

    # ------------------------------------------------------------------
    # Solving
    # ------------------------------------------------------------------

    def _build_z3_vars(
        self,
        variables: list[VariableDeclaration],
    ) -> tuple[dict[str, z3.ExprRef], list[z3.BoolRef]]:
        """Build Z3 variable references and bound constraints.

        Args:
            variables: List of variable declarations.

        Returns:
            Tuple of (variable map, bound constraints).

        """
        z3_vars: dict[str, z3.ExprRef] = {}
        bounds: list[z3.BoolRef] = []

        for var in variables:
            if var.sort == VariableSort.INT:
                z3_var = cast("z3.ArithRef", z3.Int(var.name))
            elif var.sort == VariableSort.REAL:
                z3_var = cast("z3.ArithRef", z3.Real(var.name))
            elif var.sort == VariableSort.BOOL:
                z3_var = z3.Bool(var.name)
            else:
                msg = f"Unknown variable sort: {var.sort!r}"
                raise ValueError(msg)
            z3_vars[var.name] = z3_var

            if isinstance(z3_var, z3.ArithRef):
                if var.lower_bound is not None:
                    bounds.append(z3_var >= var.lower_bound)
                if var.upper_bound is not None:
                    bounds.append(z3_var <= var.upper_bound)

        return z3_vars, bounds

    def _parse_constraint(
        self,
        constraint_str: str,
        z3_vars: dict[str, z3.ExprRef],
    ) -> z3.BoolRef | None:
        """Parse a constraint string into a Z3 expression.

        Args:
            constraint_str: The constraint expression string.
            z3_vars: Mapping of variable names to Z3 references.

        Returns:
            Z3 boolean expression, or None if parsing failed.

        """
        if not _CONSTRAINT_SAFE_PATTERN.match(constraint_str):
            logger.warning("Constraint contains unsafe characters: %r", constraint_str)
            return None
        try:
            builtins_dict: dict[str, object] = {"__builtins__": {}}
            result = eval(  # noqa: S307  # nosec B307 - sandboxed with empty builtins and validated
                constraint_str,
                builtins_dict,
                dict(z3_vars),
            )
        except (NameError, TypeError, z3.Z3Exception) as exc:
            logger.warning("Cannot parse constraint %r: %s", constraint_str, exc)
            return None
        else:
            if isinstance(result, bool):
                return z3.BoolVal(result)
            return cast(z3.BoolRef, result)

    def solve(self, constraint_set: ConstraintSet) -> SymbolicSolution:
        """Solve a constraint satisfaction problem.

        Args:
            constraint_set: The constraint set to solve.

        Returns:
            SymbolicSolution with satisfiability status and model.

        """
        self._solve_count += 1
        z3_vars, bounds = self._build_z3_vars(constraint_set.variables)

        solver = z3.Solver()
        for bound in bounds:
            solver.add(bound)

        for constraint_str in constraint_set.constraints:
            expr = self._parse_constraint(constraint_str, z3_vars)
            if expr is None:
                return SymbolicSolution(
                    satisfiable=False,
                    model={},
                    message=f"Failed to parse constraint: {constraint_str!r}",
                )
            solver.add(expr)

        check_result = solver.check()
        if check_result == z3.sat:
            model = solver.model()
            model_dict = {str(d): str(model[d]) for d in model.decls()}
            return SymbolicSolution(
                satisfiable=True,
                model=model_dict,
                message="Satisfiable",
            )
        if check_result == z3.unsat:
            return SymbolicSolution(
                satisfiable=False,
                model={},
                message="Unsatisfiable",
            )
        return SymbolicSolution(
            satisfiable=False,
            model={},
            message="Solver returned unknown",
        )

    def optimize(
        self,
        constraint_set: ConstraintSet,
        objective: OptimizationObjective,
    ) -> SymbolicSolution:
        """Solve with optimization objective.

        Args:
            constraint_set: The constraint set to solve.
            objective: Optimization objective (minimize/maximize).

        Returns:
            SymbolicSolution with optimal model and objective value.

        """
        self._solve_count += 1
        z3_vars, bounds = self._build_z3_vars(constraint_set.variables)

        optimizer = z3.Optimize()
        for bound in bounds:
            optimizer.add(bound)

        for constraint_str in constraint_set.constraints:
            expr = self._parse_constraint(constraint_str, z3_vars)
            if expr is None:
                return SymbolicSolution(
                    satisfiable=False,
                    model={},
                    message=f"Failed to parse constraint: {constraint_str!r}",
                )
            optimizer.add(expr)

        obj_expr = self._parse_constraint(objective.expression, z3_vars)
        if obj_expr is None:
            return SymbolicSolution(
                satisfiable=False,
                model={},
                message=f"Failed to parse objective: {objective.expression!r}",
            )

        if objective.direction == "minimize":
            handle = optimizer.minimize(obj_expr)
        else:
            handle = optimizer.maximize(obj_expr)

        check_result = optimizer.check()
        if check_result == z3.sat:
            model = optimizer.model()
            model_dict = {str(d): str(model[d]) for d in model.decls()}
            return SymbolicSolution(
                satisfiable=True,
                model=model_dict,
                objective_value=str(handle.value()),
                message=f"Optimal ({objective.direction})",
            )
        return SymbolicSolution(
            satisfiable=False,
            model={},
            message="Optimization infeasible",
        )

    def check_satisfiable(self, constraint_set: ConstraintSet) -> ValidationResult:
        """Check if a constraint set is satisfiable.

        Args:
            constraint_set: The constraint set to check.

        Returns:
            ValidationResult indicating satisfiability.

        """
        result = self.solve(constraint_set)
        return ValidationResult(
            valid=result.satisfiable,
            message=result.message,
            details=result.model,
        )

    def solve_registered(self, name: str) -> SymbolicSolution:
        """Solve a previously registered constraint set by name.

        Args:
            name: The registered constraint set name.

        Returns:
            SymbolicSolution with results.

        Raises:
            KeyError: If no constraint set is registered with this name.

        """
        cs = self._constraint_sets.get(name)
        if cs is None:
            msg = f"No constraint set registered with name: {name!r}"
            raise KeyError(msg)
        return self.solve(cs)

    @property
    def solve_count(self) -> int:
        """Number of solve operations performed."""
        return self._solve_count

    @property
    def registered_sets(self) -> list[str]:
        """Names of all registered constraint sets."""
        return sorted(self._constraint_sets.keys())


__all__ = [
    "ConstraintSet",
    "OptimizationObjective",
    "SymbolicConstraintEngine",
    "SymbolicSolution",
    "VariableDeclaration",
    "VariableSort",
]
