"""Adaptive finite-domain representation search with infeasibility diagnostics.

The engine chooses between exhaustive enumeration and constraint-directed search
from measurable features of a declared finite-domain problem. It verifies found
witnesses, exhaustively proves infeasibility relative to the finite input domains,
and can report a deletion-minimal conflict set with candidate repairs. No user
supplied code is executed.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import product
from math import isfinite, prod

type Scalar = str | int | float | bool
_OPERATORS = {"eq", "ne", "lt", "le", "gt", "ge"}


@dataclass(frozen=True, slots=True)
class VariableDomain:
    """One finite variable and its ordered candidate values."""
    name: str
    domain: tuple[Scalar, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            msg = "variable name must not be empty"
            raise ValueError(msg)
        if not self.domain:
            msg = f"domain for {self.name} must not be empty"
            raise ValueError(msg)
        if len(set(self.domain)) != len(self.domain):
            msg = f"domain for {self.name} contains duplicate values"
            raise ValueError(msg)
        if any(not isinstance(value, (str, int, float, bool)) for value in self.domain):
            msg = f"domain for {self.name} must contain scalar values"
            raise ValueError(msg)
        if any(isinstance(value, float) and not isfinite(value) for value in self.domain):
            msg = f"domain for {self.name} must not contain non-finite values"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class RelationConstraint:
    """Binary or unary constraint in a closed, non-executable expression format."""
    name: str
    left_variable: str
    operator: str
    right_value: Scalar | None = None
    right_variable: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.left_variable.strip():
            msg = "constraint name and left_variable must not be empty"
            raise ValueError(msg)
        if self.operator not in _OPERATORS:
            msg = f"unsupported operator: {self.operator}"
            raise ValueError(msg)
        if (self.right_value is None) == (self.right_variable is None):
            msg = "set exactly one of right_value or right_variable"
            raise ValueError(msg)
        if self.right_variable is not None and not self.right_variable.strip():
            msg = "right_variable must not be empty"
            raise ValueError(msg)
        if isinstance(self.right_value, float) and not isfinite(self.right_value):
            msg = "constraint numeric values must be finite"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class FiniteDomainProblem:
    """Finite variable domains and relations to be solved exhaustively."""
    problem_id: str
    variables: tuple[VariableDomain, ...]
    constraints: tuple[RelationConstraint, ...] = ()

    def __post_init__(self) -> None:
        if not self.problem_id.strip():
            msg = "problem_id must not be empty"
            raise ValueError(msg)
        names = [variable.name for variable in self.variables]
        if len(names) != len(set(names)):
            msg = "variable names must be unique"
            raise ValueError(msg)
        constraint_names = [constraint.name for constraint in self.constraints]
        if len(constraint_names) != len(set(constraint_names)):
            msg = "constraint names must be unique for auditable conflict cores"
            raise ValueError(msg)
        declared = set(names)
        for constraint in self.constraints:
            if constraint.left_variable not in declared:
                msg = f"undeclared variable: {constraint.left_variable}"
                raise ValueError(msg)
            if constraint.right_variable is not None and constraint.right_variable not in declared:
                msg = f"undeclared variable: {constraint.right_variable}"
                raise ValueError(msg)

    @property
    def search_space_size(self) -> int:
        """Return the number of assignments before pruning."""
        return prod(len(variable.domain) for variable in self.variables)


@dataclass(frozen=True, slots=True)
class SolverMetrics:
    """Measured deterministic workload for one solver implementation."""
    strategy: str
    satisfiable: bool
    solution: tuple[tuple[str, Scalar], ...] | None
    nodes_expanded: int
    assignments_checked: int
    complete: bool = True


@dataclass(frozen=True, slots=True)
class RepresentationReport:
    """Auditable representation choice, measured alternatives and feasibility result."""
    report_id: str
    problem_id: str
    selected_strategy: str
    selection_reason: str
    search_space_size: int
    constraint_density: float
    selected_result: SolverMetrics
    comparison_runs: tuple[SolverMetrics, ...]
    verification_status: str
    verified: bool
    conflict_core: tuple[str, ...]
    repair_candidates: tuple[dict[str, str], ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible report."""
        return json.loads(json.dumps(asdict(self)))


def _compare(left: Scalar, operator: str, right: Scalar) -> bool:
    """Apply one validated relation; incompatible value types are an input error."""
    if operator == "eq":
        return left == right
    if operator == "ne":
        return left != right
    try:
        if operator == "lt":
            return left < right
        if operator == "le":
            return left <= right
        if operator == "gt":
            return left > right
        if operator == "ge":
            return left >= right
    except TypeError as exc:
        msg = f"incompatible values for {operator}: {left!r}, {right!r}"
        raise ValueError(msg) from exc
    msg = f"unsupported operator: {operator}"
    raise ValueError(msg)


def _partial_consistent(
    assignment: dict[str, Scalar], constraints: tuple[RelationConstraint, ...],
) -> bool:
    """Check any constraint whose operands are already bound."""
    for constraint in constraints:
        if constraint.left_variable not in assignment:
            continue
        if constraint.right_variable is not None:
            if constraint.right_variable not in assignment:
                continue
            right = assignment[constraint.right_variable]
        else:
            right = constraint.right_value
        if not _compare(assignment[constraint.left_variable], constraint.operator, right):
            return False
    return True


def _run_solver(problem: FiniteDomainProblem, strategy: str) -> SolverMetrics:
    """Run one complete solver and count deterministic search work."""
    if strategy not in {"enumeration", "fixed_order", "mrv"}:
        msg = f"unsupported strategy: {strategy}"
        raise ValueError(msg)
    variables = problem.variables
    constraints = problem.constraints
    nodes = 0
    checked = 0

    if strategy == "enumeration":
        domains = [variable.domain for variable in variables]
        for candidate in product(*domains):
            checked += 1
            nodes += 1
            assignment = {v.name: candidate[i] for i, v in enumerate(variables)}
            if _partial_consistent(assignment, constraints):
                return SolverMetrics(strategy, True, tuple(assignment.items()), nodes, checked)
        return SolverMetrics(strategy, False, None, nodes, checked)

    original_order = {variable.name: index for index, variable in enumerate(variables)}
    degrees = {variable.name: 0 for variable in variables}
    for constraint in constraints:
        if constraint.right_variable is not None:
            degrees[constraint.left_variable] += 1
            degrees[constraint.right_variable] += 1
    assignment: dict[str, Scalar] = {}

    def visit() -> dict[str, Scalar] | None:
        nonlocal nodes, checked
        nodes += 1
        if len(assignment) == len(variables):
            checked += 1
            return dict(assignment)
        unassigned = [v for v in variables if v.name not in assignment]
        if strategy == "fixed_order":
            chosen = min(unassigned, key=lambda item: original_order[item.name])
            candidates = [value for value in chosen.domain if _partial_consistent(
                {**assignment, chosen.name: value}, constraints,
            )]
        else:
            remaining: list[tuple[int, int, int, VariableDomain, list[Scalar]]] = []
            for variable in unassigned:
                viable = [value for value in variable.domain if _partial_consistent(
                    {**assignment, variable.name: value}, constraints,
                )]
                remaining.append((len(viable), -degrees[variable.name],
                                  original_order[variable.name], variable, viable))
            remaining.sort(key=lambda item: (item[0], item[1], item[2]))
            viable_count, _, _, chosen, candidates = remaining[0]
            if viable_count == 0:
                return None
        for value in candidates:
            assignment[chosen.name] = value
            answer = visit()
            if answer is not None:
                return answer
            del assignment[chosen.name]
        return None

    solution = visit()
    ordered = tuple((v.name, solution[v.name]) for v in variables) if solution is not None else None
    return SolverMetrics(strategy, solution is not None, ordered, nodes, checked)


def _minimal_conflict_core(problem: FiniteDomainProblem) -> tuple[str, ...]:
    """Find a deletion-minimal unsatisfiable constraint set for a finite-domain model."""
    core = list(problem.constraints)
    if _run_solver(problem, "mrv").satisfiable:
        return ()
    for constraint in tuple(core):
        candidate = [item for item in core if item.name != constraint.name]
        reduced = FiniteDomainProblem(problem.problem_id, problem.variables, tuple(candidate))
        if not _run_solver(reduced, "mrv").satisfiable:
            core = candidate
    return tuple(item.name for item in core)


class AdaptiveRepresentationEngine:
    """Choose a finite-domain search representation using instance structure."""
    MAX_BASELINE_SPACE = 50000

    def solve(self, problem: FiniteDomainProblem) -> RepresentationReport:
        """Select a strategy, verify its witness/verdict, and report alternatives."""
        space = problem.search_space_size
        variable_count = len(problem.variables)
        pair_capacity = max(1, variable_count * (variable_count - 1) // 2)
        binary_count = sum(c.right_variable is not None for c in problem.constraints)
        unary_count = len(problem.constraints) - binary_count
        density = min(1.0, binary_count / pair_capacity)
        if space <= 128:
            strategy = "enumeration"
            reason = "The finite Cartesian search space is small; direct enumeration has low overhead."
        elif problem.constraints and (
            unary_count > 0 or density >= 0.15
            or len(problem.constraints) / max(1, variable_count) >= 0.7
        ):
            strategy = "mrv"
            reason = "Unary restrictions or constraint density make fail-first selection a useful pruning strategy."
        elif problem.constraints:
            strategy = "fixed_order"
            reason = "The search space is larger than the enumeration cutoff but constraints are sparse."
        else:
            strategy = "enumeration"
            reason = "No constraints are declared; exhaustive search has no constraint-pruning advantage."

        selected = _run_solver(problem, strategy)
        if selected.satisfiable:
            solution = dict(selected.solution or ())
            verified = _partial_consistent(solution, problem.constraints)
            status = "witness_verified" if verified else "verification_failed"
            core: tuple[str, ...] = ()
            repairs: tuple[dict[str, str], ...] = ()
        else:
            verified = selected.complete
            status = "finite_domain_unsatisfiable" if verified else "unknown"
            core = _minimal_conflict_core(problem) if problem.constraints else ()
            repair_list: list[dict[str, str]] = []
            for name in core:
                reduced_constraints = tuple(c for c in problem.constraints if c.name != name)
                reduced = FiniteDomainProblem(problem.problem_id, problem.variables, reduced_constraints)
                if _run_solver(reduced, "mrv").satisfiable:
                    repair_list.append({
                        "constraint": name,
                        "action": "review_or_relax",
                        "explanation": (
                            "Removing this constraint restores feasibility under the remaining declared model; "
                            "check whether the condition is wrong or the variable domain is incomplete."
                        ),
                    })
            repairs = tuple(repair_list)

        runs = [selected]
        notes: list[str] = [
            "All verdicts are bounded to the finite domains and relation operators declared in the input.",
            "A verified solution is a witness checked against every declared constraint.",
            "An unsatisfiable result means exhaustive search found no assignment within the declared finite domains.",
            "A deletion-minimal conflict core is not guaranteed to be the unique or smallest-cardinality core.",
            "Repair candidates identify constraints to review; they do not authorize silently changing user requirements.",
        ]
        if space <= self.MAX_BASELINE_SPACE:
            for alternative in ("enumeration", "fixed_order", "mrv"):
                if alternative != strategy:
                    runs.append(_run_solver(problem, alternative))
            verdicts = {run.satisfiable for run in runs}
            if len(verdicts) != 1:
                notes.append("WARNING: solver implementations disagreed; treat the report as unverified.")
                verified = False
                status = "solver_disagreement"
        else:
            notes.append(
                f"Baseline comparison limited: Cartesian space {space} exceeds audit cutoff "
                f"{self.MAX_BASELINE_SPACE}."
            )
        identity = json.dumps({
            "problem_id": problem.problem_id,
            "variables": [asdict(v) for v in problem.variables],
            "constraints": [asdict(c) for c in problem.constraints],
            "selected_strategy": strategy,
        }, sort_keys=True, default=str, separators=(",", ":"))
        return RepresentationReport(
            report_id=sha256(identity.encode()).hexdigest()[:24], problem_id=problem.problem_id,
            selected_strategy=strategy, selection_reason=reason, search_space_size=space,
            constraint_density=round(density, 4), selected_result=selected,
            comparison_runs=tuple(runs), verification_status=status, verified=verified,
            conflict_core=core, repair_candidates=repairs, notes=tuple(notes),
        )
