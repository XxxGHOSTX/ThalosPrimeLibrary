"""Library of Sense - Proof Checker.

Verifies mathematical proofs by checking symbolic equivalence and
evaluating propositional tautologies using sympy.
"""

from __future__ import annotations

import logging

import sympy

from thalos_prime.library_of_sense.core.interfaces import ValidationResult

logger = logging.getLogger(__name__)


class ProofChecker:
    """Verifies mathematical statements and algebraic identities using sympy.

    Checks equivalence between expressions and validates algebraic identities
    using sympy's symbolic computation capabilities.
    """

    def check_equivalence(self, lhs: str, rhs: str) -> ValidationResult:
        """Check if two mathematical expressions are symbolically equivalent.

        Args:
            lhs: Left-hand side expression string.
            rhs: Right-hand side expression string.

        Returns:
            ValidationResult indicating whether lhs == rhs symbolically.
        """
        try:
            left = sympy.sympify(lhs)
            right = sympy.sympify(rhs)
            difference = sympy.simplify(left - right)
            equivalent = difference == 0
            return ValidationResult(
                valid=equivalent,
                message=(
                    f"{lhs} == {rhs} (verified)"
                    if equivalent
                    else f"{lhs} != {rhs} (difference={difference})"
                ),
                details={
                    "lhs": str(left),
                    "rhs": str(right),
                    "difference": str(difference),
                },
            )
        except (sympy.SympifyError, TypeError) as exc:
            return ValidationResult(
                valid=False,
                message=f"Cannot check equivalence: {exc}",
                details={"error": str(exc)},
            )

    def check_identity(self, expression: str) -> ValidationResult:
        """Check if an expression equals zero when expanded (algebraic identity check).

        Args:
            expression: Mathematical expression that should equal zero if the identity holds.

        Returns:
            ValidationResult indicating whether the identity holds.
        """
        try:
            expr = sympy.sympify(expression)
            expanded = sympy.expand(expr)
            simplified = sympy.simplify(expanded)
            is_identity = simplified == 0
            return ValidationResult(
                valid=is_identity,
                message=(
                    f"Identity holds: {expression} = 0"
                    if is_identity
                    else f"Not an identity: {simplified}"
                ),
                details={
                    "expression": str(expr),
                    "simplified": str(simplified),
                },
            )
        except (sympy.SympifyError, TypeError) as exc:
            return ValidationResult(
                valid=False,
                message=f"Cannot check identity: {exc}",
                details={"error": str(exc)},
            )


__all__ = ["ProofChecker"]
