"""Library of Sense - Constraint Solver.

Uses z3-solver to check satisfiability and solve systems of
arithmetic constraints over integer and real domains.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal

import z3

from thalos_prime.library_of_sense.core.interfaces import ValidationResult

logger = logging.getLogger(__name__)

SatisfiabilityStatus = Literal["sat", "unsat", "unknown"]

# Allowed pattern: variable names, digits, arithmetic operators, comparisons, whitespace
_CONSTRAINT_SAFE_PATTERN = re.compile(r"^[\w\s\+\-\*\/\(\)\<\>\=\!\.]+$")


@dataclass
class ConstraintProblem:
    """Describes a constraint satisfaction problem with named variables and assertions."""

    int_vars: list[str] = field(default_factory=list)
    real_vars: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this constraint problem.

        """
        return {
            "int_vars": list(self.int_vars),
            "real_vars": list(self.real_vars),
            "constraints": list(self.constraints),
        }


@dataclass
class SolverResult:
    """Result from a z3 constraint solving operation."""

    status: SatisfiabilityStatus
    model: dict[str, str]
    message: str

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this solver result.

        """
        return {
            "status": self.status,
            "model": self.model,
            "message": self.message,
        }


class ConstraintSolver:
    """Solves constraint satisfaction problems using z3-solver.

    Builds z3 solver instances from ConstraintProblem descriptions and
    returns satisfiability status with concrete models when SAT.
    """

    def solve(self, problem: ConstraintProblem) -> SolverResult:
        """Solve a constraint satisfaction problem using z3.

        Args:
            problem: ConstraintProblem defining variables and constraints.

        Returns:
            SolverResult with satisfiability status and model values.

        """
        solver = z3.Solver()
        z3_vars: dict[str, z3.ExprRef] = {}

        for var_name in problem.int_vars:
            z3_vars[var_name] = z3.Int(var_name)
        for var_name in problem.real_vars:
            z3_vars[var_name] = z3.Real(var_name)

        for constraint_str in problem.constraints:
            if not _CONSTRAINT_SAFE_PATTERN.match(constraint_str):
                msg = f"Constraint contains unsafe characters: {constraint_str!r}"
                logger.warning("ConstraintSolver: %s", msg)
                return SolverResult(status="unknown", model={}, message=msg)
            try:
                constraint_expr = eval(  # noqa: S307 - sandboxed with empty builtins and validated pattern
                    constraint_str,
                    {"__builtins__": {}},
                    z3_vars,
                )
                solver.add(constraint_expr)
            except (NameError, TypeError, z3.Z3Exception) as exc:
                logger.warning(
                    "ConstraintSolver: cannot parse constraint %r: %s",
                    constraint_str,
                    exc,
                )
                return SolverResult(
                    status="unknown",
                    model={},
                    message=f"Constraint parse error: {exc}",
                )

        check_result = solver.check()

        if check_result == z3.sat:
            model = solver.model()
            model_dict = {str(d): str(model[d]) for d in model.decls()}
            return SolverResult(
                status="sat",
                model=model_dict,
                message="Satisfiable",
            )
        if check_result == z3.unsat:
            return SolverResult(
                status="unsat",
                model={},
                message="Unsatisfiable",
            )
        return SolverResult(
            status="unknown",
            model={},
            message="Solver returned unknown",
        )

    def check_satisfiable(self, problem: ConstraintProblem) -> ValidationResult:
        """Check if a constraint problem is satisfiable.

        Args:
            problem: ConstraintProblem to check.

        Returns:
            ValidationResult indicating satisfiability.

        """
        result = self.solve(problem)
        return ValidationResult(
            valid=result.status == "sat",
            message=result.message,
            details=result.model,
        )


__all__ = ["ConstraintProblem", "ConstraintSolver", "SolverResult"]
