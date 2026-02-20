"""Library of Sense - Symbolic Reasoning Engine.

Uses sympy for symbolic mathematics: expression parsing, simplification,
differentiation, integration, and algebraic proof steps.
"""

from __future__ import annotations

import logging

import sympy
from sympy import Expr, Symbol, symbols

from thalos_prime.library_of_sense.core.interfaces import (
    QueryContext,
    ReasoningResult,
)

logger = logging.getLogger(__name__)


class SymbolicReasoningEngine:
    """Performs symbolic mathematical reasoning using sympy.

    Parses mathematical expressions, simplifies them, and produces
    deterministic proof steps via symbolic computation.
    """

    def simplify_expression(self, expr_str: str) -> tuple[str, list[str]]:
        """Parse and simplify a sympy-compatible expression.

        Args:
            expr_str: Mathematical expression string.

        Returns:
            Tuple of (simplified expression string, list of proof steps).

        Raises:
            ValueError: If the expression cannot be parsed.

        """
        try:
            expr: Expr = sympy.sympify(expr_str)
        except (sympy.SympifyError, TypeError) as exc:
            msg = f"Cannot parse expression {expr_str!r}: {exc}"
            raise ValueError(msg) from exc

        simplified = sympy.simplify(expr)
        steps = [
            f"Original expression: {expr}",
            f"Simplified: {simplified}",
        ]
        return str(simplified), steps

    def differentiate(
        self, expr_str: str, var_name: str = "x",
    ) -> tuple[str, list[str]]:
        """Compute the derivative of an expression with respect to a variable.

        Args:
            expr_str: Mathematical expression string.
            var_name: Variable name to differentiate with respect to.

        Returns:
            Tuple of (derivative string, list of proof steps).

        Raises:
            ValueError: If the expression cannot be parsed.

        """
        try:
            var: Symbol = symbols(var_name)
            expr: Expr = sympy.sympify(expr_str)
            derivative = sympy.diff(expr, var)
            simplified_deriv = sympy.simplify(derivative)
        except (sympy.SympifyError, TypeError) as exc:
            msg = f"Cannot differentiate {expr_str!r}: {exc}"
            raise ValueError(msg) from exc

        steps = [
            f"d/d{var_name}({expr}) = {derivative}",
            f"Simplified derivative: {simplified_deriv}",
        ]
        return str(simplified_deriv), steps

    def reason(self, premise: str, context: QueryContext) -> ReasoningResult:
        """Apply symbolic reasoning to a mathematical premise.

        Args:
            premise: A mathematical expression or equation to reason about.
            context: Query context providing execution options.

        Returns:
            ReasoningResult with simplified form and proof steps.

        """
        _ = context
        try:
            simplified, steps = self.simplify_expression(premise)
            return ReasoningResult(
                conclusion=simplified,
                proof_steps=steps,
                valid=True,
                confidence=0.95,
            )
        except ValueError as exc:
            logger.debug(
                "SymbolicReasoningEngine: reasoning failed for %r: %s", premise, exc,
            )
            return ReasoningResult(
                conclusion="",
                proof_steps=[f"Reasoning failed: {exc}"],
                valid=False,
                confidence=0.0,
            )


__all__ = ["SymbolicReasoningEngine"]
