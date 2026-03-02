"""Thalos Prime - Reasoning Control Plane.

Control Plane component that coordinates symbolic reasoning, proof checking,
and constraint solving under a unified lifecycle interface.

Control Plane boundary: coordinates lifecycle and state for reasoning
subsystems. Delegates computational work to Data Plane components
(SymbolicReasoningEngine, ProofChecker, ConstraintSolver).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from thalos_prime.library_of_sense.core.interfaces import (
    QueryContext,
    QueryDomain,
    ReasoningResult,
    ValidationResult,
)
from thalos_prime.library_of_sense.reasoning.constraint_solver import (
    ConstraintProblem,
    ConstraintSolver,
    SolverResult,
)
from thalos_prime.library_of_sense.reasoning.proof_checker import ProofChecker
from thalos_prime.library_of_sense.reasoning.symbolic_engine import (
    SymbolicReasoningEngine,
)
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)

ReasoningMode = Literal["symbolic", "proof", "constraint"]


@dataclass
class ReasoningRequest:
    """A request to the reasoning control plane.

    Attributes:
        premise: The statement or expression to reason about.
        mode: Which reasoning engine to dispatch to.
        constraint_problem: Optional constraint problem for constraint mode.
        proof_lhs: Left-hand side for proof equivalence checking.
        proof_rhs: Right-hand side for proof equivalence checking.

    """

    premise: str
    mode: ReasoningMode = "symbolic"
    constraint_problem: ConstraintProblem | None = None
    proof_lhs: str = ""
    proof_rhs: str = ""


@dataclass
class ReasoningResponse:
    """Aggregated response from the reasoning control plane.

    Attributes:
        mode: Which reasoning engine produced this response.
        result: The reasoning result (for symbolic mode).
        solver_result: The solver result (for constraint mode).
        validation: The validation result (for proof mode).
        steps: Ordered list of reasoning steps for audit trail.

    """

    mode: ReasoningMode
    result: ReasoningResult | None = None
    solver_result: SolverResult | None = None
    validation: ValidationResult | None = None
    steps: list[str] = field(default_factory=list)


class ReasoningControlPlane(BaseLifecycleComponent):
    """Control Plane that coordinates reasoning subsystems.

    Orchestrates SymbolicReasoningEngine, ProofChecker, and ConstraintSolver
    under a unified lifecycle with deterministic event logging.
    """

    def __init__(self, seed: int = 0) -> None:
        """Initialize the reasoning control plane.

        Args:
            seed: Deterministic seed for replay identification.

        """
        super().__init__("ReasoningControlPlane", seed=seed)
        self._symbolic_engine = SymbolicReasoningEngine()
        self._proof_checker = ProofChecker()
        self._constraint_solver = ConstraintSolver()
        self._request_count: int = 0
        self._error_count: int = 0

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize all reasoning subsystems."""
        self._request_count = 0
        self._error_count = 0
        self._initialized = True
        self._emit_event("initialize", "reasoning subsystems ready")
        logger.debug("ReasoningControlPlane initialized")

    def validate(self) -> ValidationResult:
        """Validate that all reasoning subsystems are ready.

        Returns:
            ValidationResult indicating readiness.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="ReasoningControlPlane not initialized; call initialize() first",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"ReasoningControlPlane ready: requests={self._request_count} "
                f"errors={self._error_count}"
            ),
        )

    def operate(self) -> None:
        """Log current reasoning statistics. Idempotent."""
        self._emit_event(
            "operate",
            f"requests={self._request_count} errors={self._error_count}",
        )

    def reconcile(self) -> None:
        """Reconcile counters to non-negative values."""
        self._request_count = max(self._request_count, 0)
        self._error_count = max(self._error_count, 0)
        self._emit_event(
            "reconcile",
            f"requests={self._request_count} errors={self._error_count}",
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialize reasoning control plane state.

        Returns:
            Dict with component name, seed, and operation counters.

        """
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "request_count": self._request_count,
            "error_count": self._error_count,
        }
        self._emit_event("checkpoint", f"requests={self._request_count}")
        return state

    def terminate(self) -> None:
        """Reset reasoning control plane state."""
        self._request_count = 0
        self._error_count = 0
        self._initialized = False
        self._emit_event("terminate", "counters reset, initialized=False")
        logger.debug("ReasoningControlPlane terminated")

    # ------------------------------------------------------------------
    # Control Plane dispatch methods
    # ------------------------------------------------------------------

    def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        """Dispatch a reasoning request to the appropriate subsystem.

        Routes requests based on mode: symbolic reasoning, proof checking,
        or constraint solving. All dispatch decisions are logged.

        Args:
            request: The reasoning request to process.

        Returns:
            ReasoningResponse with results from the selected engine.

        Raises:
            RuntimeError: If the control plane is not initialized.

        """
        if not self._initialized:
            msg = "ReasoningControlPlane not initialized; call initialize() first"
            raise RuntimeError(msg)

        self._request_count += 1
        steps: list[str] = [f"Dispatching to {request.mode} engine"]

        if request.mode == "symbolic":
            return self._dispatch_symbolic(request, steps)
        if request.mode == "proof":
            return self._dispatch_proof(request, steps)
        return self._dispatch_constraint(request, steps)

    def _dispatch_symbolic(
        self,
        request: ReasoningRequest,
        steps: list[str],
    ) -> ReasoningResponse:
        """Dispatch to the symbolic reasoning engine.

        Args:
            request: The reasoning request.
            steps: Mutable list of audit trail steps.

        Returns:
            ReasoningResponse with symbolic reasoning result.

        """
        context = QueryContext(domain=QueryDomain.MATHEMATICS, seed=self._seed)
        result = self._symbolic_engine.reason(request.premise, context)
        steps.extend(result.proof_steps)

        if not result.valid:
            self._error_count += 1

        self._emit_event(
            "reason",
            f"mode=symbolic valid={result.valid} confidence={result.confidence}",
        )
        return ReasoningResponse(
            mode="symbolic",
            result=result,
            steps=steps,
        )

    def _dispatch_proof(
        self,
        request: ReasoningRequest,
        steps: list[str],
    ) -> ReasoningResponse:
        """Dispatch to the proof checker.

        Args:
            request: The reasoning request with proof_lhs and proof_rhs.
            steps: Mutable list of audit trail steps.

        Returns:
            ReasoningResponse with proof validation result.

        """
        if request.proof_lhs and request.proof_rhs:
            validation = self._proof_checker.check_equivalence(
                request.proof_lhs,
                request.proof_rhs,
            )
            steps.append(
                f"Equivalence check: {request.proof_lhs} == {request.proof_rhs}",
            )
        else:
            validation = self._proof_checker.check_identity(request.premise)
            steps.append(f"Identity check: {request.premise} == 0")

        steps.append(f"Result: {validation.message}")

        if not validation.valid:
            self._error_count += 1

        self._emit_event(
            "reason",
            f"mode=proof valid={validation.valid}",
        )
        return ReasoningResponse(
            mode="proof",
            validation=validation,
            steps=steps,
        )

    def _dispatch_constraint(
        self,
        request: ReasoningRequest,
        steps: list[str],
    ) -> ReasoningResponse:
        """Dispatch to the constraint solver.

        Args:
            request: The reasoning request with constraint_problem.
            steps: Mutable list of audit trail steps.

        Returns:
            ReasoningResponse with constraint solving result.

        """
        problem = request.constraint_problem or ConstraintProblem()
        solver_result = self._constraint_solver.solve(problem)
        steps.append(f"Constraint solver status: {solver_result.status}")

        if solver_result.status != "sat":
            self._error_count += 1

        self._emit_event(
            "reason",
            f"mode=constraint status={solver_result.status}",
        )
        return ReasoningResponse(
            mode="constraint",
            solver_result=solver_result,
            steps=steps,
        )


__all__ = [
    "ReasoningControlPlane",
    "ReasoningMode",
    "ReasoningRequest",
    "ReasoningResponse",
]
