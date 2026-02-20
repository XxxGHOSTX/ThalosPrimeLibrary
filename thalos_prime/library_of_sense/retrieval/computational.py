"""Library of Sense - Computational Retrieval.

Evaluates mathematical expressions and symbolic computations using sympy
to provide numerically and symbolically verified answers.
"""

from __future__ import annotations

import logging

import sympy

from thalos_prime.library_of_sense.core.interfaces import (
    QueryContext,
    RetrievalResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)

_SYMPY_SANITY_CHECK = 2


class ComputationalRetriever:
    """Retrieves answers by evaluating mathematical expressions with sympy.

    Attempts to parse and evaluate the query as a sympy expression, returning
    both the symbolic and numerical forms of the result.
    """

    def query(self, query: str, context: QueryContext) -> RetrievalResult:
        """Evaluate a mathematical expression and return the result.

        Args:
            query: Mathematical expression or equation to evaluate.
            context: Query context with domain and execution options.

        Returns:
            RetrievalResult with symbolic and numeric evaluation results.
        """
        _ = context
        try:
            expr = sympy.sympify(query)
            simplified = sympy.simplify(expr)
            numeric = sympy.N(simplified)
            content = f"symbolic={simplified}, numeric={numeric}"
            return RetrievalResult(
                source="computational",
                content=content,
                confidence=0.95,
                metadata={
                    "expression": query,
                    "simplified": str(simplified),
                    "numeric": str(numeric),
                },
            )
        except (sympy.SympifyError, TypeError, ValueError) as exc:
            logger.debug("ComputationalRetriever: cannot evaluate %r: %s", query, exc)
            return RetrievalResult(
                source="computational",
                content="",
                confidence=0.0,
                metadata={"reason": "evaluation_error", "expression": query},
            )

    def validate(self) -> ValidationResult:
        """Validate the computational retriever.

        Returns:
            ValidationResult indicating sympy is available and functional.
        """
        test_expr = sympy.sympify("1 + 1")
        if int(test_expr) != _SYMPY_SANITY_CHECK:
            return ValidationResult(
                valid=False,
                message="sympy sanity check failed",
            )
        return ValidationResult(
            valid=True,
            message=f"ComputationalRetriever ready (sympy {sympy.__version__})",
        )

    def initialize(self) -> None:
        """Initialize the computational retriever."""
        logger.debug("ComputationalRetriever initialized")

    def operate(self) -> None:
        """Transition to operating state."""
        logger.debug("ComputationalRetriever operating")

    def reconcile(self) -> None:
        """Reconcile computational retriever state."""
        logger.debug("ComputationalRetriever reconcile")

    def checkpoint(self) -> None:
        """Log current state as a checkpoint."""
        logger.info("ComputationalRetriever checkpoint: sympy=%s", sympy.__version__)

    def terminate(self) -> None:
        """Terminate the computational retriever."""
        logger.debug("ComputationalRetriever terminated")


__all__ = ["ComputationalRetriever"]
