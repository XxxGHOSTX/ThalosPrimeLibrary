"""Deterministic, evidence-aware discovery primitives.

This engine turns a problem into explicit candidate hypotheses, predictions,
falsifiers, representation transfers, contradictions, and safe constraint checks.
Generated analogies are candidates, never facts. No user-supplied code is run.
"""
from __future__ import annotations

import json
from math import isfinite
from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256
from typing import TypeAlias

Scalar: TypeAlias = str | int | float | bool


class ConstraintStatus(StrEnum):
    """Result of checking a constraint against the supplied values."""
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    UNKNOWN = "unknown"


class HypothesisStatus(StrEnum):
    """Evidence state, not a guarantee of formal truth."""
    CANDIDATE = "candidate"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    CONTESTED = "contested"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True, slots=True)
class Evidence:
    """Evidence statement with source and verification metadata."""
    evidence_id: str
    statement: str
    source_uri: str | None = None
    evidence_kind: str = "unspecified"
    independently_checked: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.statement.strip():
            raise ValueError("evidence_id and statement must not be empty")
        allowed = {"measurement", "experiment", "dataset", "paper", "record",
                   "expert_assessment", "simulation", "unspecified"}
        if self.evidence_kind not in allowed:
            raise ValueError(f"unsupported evidence_kind: {self.evidence_kind}")


@dataclass(frozen=True, slots=True)
class Claim:
    """A claim; exact contradiction checks use proposition_key and polarity."""
    claim_id: str
    text: str
    domain: str = "unspecified"
    proposition_key: str | None = None
    polarity: bool = True
    assumptions: tuple[str, ...] = ()
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        if not self.claim_id.strip() or not self.text.strip():
            raise ValueError("claim_id and text must not be empty")
        if self.proposition_key is not None and not self.proposition_key.strip():
            raise ValueError("proposition_key must be omitted or non-empty")


@dataclass(frozen=True, slots=True)
class Constraint:
    """A declarative comparison evaluated without dynamic code execution."""
    name: str
    left_variable: str
    operator: str
    right_value: Scalar | None = None
    right_variable: str | None = None
    explanation: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.left_variable.strip():
            raise ValueError("constraint name and left_variable must not be empty")
        if self.operator not in {"eq", "ne", "lt", "le", "gt", "ge"}:
            raise ValueError(f"unsupported operator: {self.operator}")
        if (self.right_value is None) == (self.right_variable is None):
            raise ValueError("set exactly one of right_value or right_variable")
        if self.right_variable is not None and not self.right_variable.strip():
            raise ValueError("right_variable must not be empty")
        if isinstance(self.right_value, float) and not isfinite(self.right_value):
            raise ValueError("constraint numeric values must be finite")

    def evaluate(self, values: dict[str, Scalar]) -> ConstraintResult:
        """Check the condition or mark it unknown when values are unavailable."""
        if self.left_variable not in values:
            return ConstraintResult(self.name, ConstraintStatus.UNKNOWN,
                                   f"Missing value for {self.left_variable}")
        if self.right_variable is not None:
            if self.right_variable not in values:
                return ConstraintResult(self.name, ConstraintStatus.UNKNOWN,
                                        f"Missing value for {self.right_variable}")
            right: Scalar | None = values[self.right_variable]
        else:
            right = self.right_value
        left = values[self.left_variable]
        try:
            passed = _compare(left, self.operator, right)
        except (TypeError, ValueError):
            return ConstraintResult(
                self.name, ConstraintStatus.UNKNOWN,
                f"Values cannot be compared: {left!r} {self.operator} {right!r}",
                actual=left, expected=right,
            )
        return ConstraintResult(
            self.name, ConstraintStatus.SATISFIED if passed else ConstraintStatus.VIOLATED,
            self.explanation or f"Checked {self.left_variable} {self.operator} right operand",
            actual=left, expected=right,
        )


@dataclass(frozen=True, slots=True)
class ConstraintResult:
    """Status plus the actual and expected values used in evaluation."""
    name: str
    status: ConstraintStatus
    detail: str
    actual: Scalar | None = None
    expected: Scalar | None = None


@dataclass(frozen=True, slots=True)
class Observation:
    """Reported experiment/test result linked to a generated hypothesis."""
    observation_id: str
    hypothesis_id: str
    outcome: str
    method: str
    source_uri: str | None = None
    setup_hash: str | None = None
    reproducible: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.observation_id.strip() or not self.hypothesis_id.strip():
            raise ValueError("observation_id and hypothesis_id must not be empty")
        if self.outcome not in {"supports", "refutes", "inconclusive"}:
            raise ValueError("outcome must be supports, refutes, or inconclusive")
        if not self.method.strip():
            raise ValueError("method must describe how the observation was obtained")
        if self.reproducible and not self.setup_hash:
            raise ValueError("reproducible observations require a setup_hash")


@dataclass(frozen=True, slots=True)
class Hypothesis:
    """Cross-domain candidate with an invariant, prediction and falsifier."""
    hypothesis_id: str
    pattern_id: str
    pattern_name: str
    source_domain: str
    target_domain: str
    representation: str
    statement: str
    invariant: str
    prediction: str
    falsifier: str
    test_plan: tuple[str, ...]
    matched_terms: tuple[str, ...]
    match_strength: float
    status: HypothesisStatus = HypothesisStatus.CANDIDATE
    supporting_observations: tuple[str, ...] = ()
    refuting_observations: tuple[str, ...] = ()
    novelty_status: str = "not_checked"


@dataclass(frozen=True, slots=True)
class DiscoveryReport:
    """Auditable result, including uncertainty and limitations."""
    report_id: str
    question: str
    representation_choices: tuple[dict[str, str], ...]
    hypotheses: tuple[Hypothesis, ...]
    observations: tuple[Observation, ...]
    contradictions: tuple[dict[str, str], ...]
    constraint_results: tuple[ConstraintResult, ...]
    missing_information: tuple[str, ...]
    unmatched_observations: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable report with enum values normalized."""
        return json.loads(json.dumps(asdict(self)))


@dataclass(frozen=True, slots=True)
class _Pattern:
    """One explicit structural transfer, with predeclared test criteria."""
    pattern_id: str
    name: str
    triggers: tuple[str, ...]
    source_domain: str
    target_domain: str
    representation: str
    statement: str
    invariant: str
    prediction: str
    falsifier: str
    tests: tuple[str, ...]


_PATTERNS: tuple[_Pattern, ...] = (
    _Pattern(
        "capacity_bottleneck", "Capacity bottleneck transfer",
        ("bottleneck", "capacity", "throughput", "limit", "saturation", "slow", "performance"),
        "operations research", "network flow and queueing theory", "capacity graph",
        "Represent each stage as a node or edge with a measured capacity, then locate the limiting cut.",
        "Sustained throughput is bounded by the limiting capacity when stages are coupled in series.",
        "Increasing capacity at the measured limiting stage should improve end-to-end throughput more than an equal-cost increase at a non-limiting stage.",
        "Matched experiments show that increasing the identified stage's capacity does not improve throughput while demand and other conditions remain comparable.",
        ("Measure each stage under comparable demand.", "Identify the minimum-capacity stage or cut.",
         "Change only that stage, then compare throughput with a control."),
    ),
    _Pattern(
        "feedback_loop", "Feedback-control transfer",
        ("feedback", "oscillation", "unstable", "overshoot", "drift", "oscillate"),
        "control engineering", "causal systems and dynamical systems", "state-transition graph",
        "Represent actions and observations as a feedback loop with delay, gain, and bounded state.",
        "Delayed corrective feedback can amplify overshoot instead of reducing error.",
        "Reducing feedback delay or gain should reduce oscillation when delayed feedback is the dominant cause.",
        "Controlled tests show unchanged or increased oscillation after reducing the implicated delay or gain.",
        ("Record state, action, delay and error over time.", "Estimate feedback delay and gain.",
         "Vary one control parameter while holding other factors constant."),
    ),
    _Pattern(
        "threshold_effect", "Threshold and phase-transition transfer",
        ("threshold", "tipping point", "cliff", "suddenly", "critical level", "nonlinear"),
        "statistical decision theory", "nonlinear systems", "thresholded state model",
        "Compare the system with a thresholded response model rather than assuming a linear response.",
        "A thresholded system can change sharply near a critical region despite small input changes.",
        "Measurements near the proposed threshold should show a reproducible change in slope or state.",
        "Adequately powered measurements across the region fit a smooth model without the proposed change.",
        ("Define the output and candidate threshold before testing.", "Collect measurements on both sides.",
         "Compare threshold and smooth models on held-out data."),
    ),
    _Pattern(
        "redundancy", "Redundancy and fault-tolerance transfer",
        ("redundancy", "backup", "resilience", "fault tolerance", "single point of failure"),
        "distributed systems", "reliability engineering", "dependency and failure graph",
        "Model components and dependencies as a graph, then identify shared failure points.",
        "Nominal redundancy does not provide resilience if redundant paths share a common failure point.",
        "Removing a shared dependency should cause correlated failures across supposedly independent paths.",
        "Independently tested paths remain available under targeted failure of the alleged shared dependency.",
        ("Map all dependency edges.", "Test independence assumptions for redundant paths.",
         "Perform a controlled failure-injection test in a safe environment."),
    ),
    _Pattern(
        "resource_allocation", "Resource-allocation transfer",
        ("resource allocation", "allocate", "budget", "capacity planning", "scarcity", "tradeoff"),
        "operations research", "optimization and scheduling", "resource-constraint graph",
        "Express scarce resources, tasks and outcomes as a constrained optimization problem.",
        "A resource allocation can improve the objective without adding resources if it removes a binding mismatch.",
        "A feasible reallocation should improve the chosen objective without violating declared constraints.",
        "The proposed allocation violates a hard constraint or fails to improve the objective in a controlled comparison.",
        ("Declare the objective and hard constraints.", "Measure the current allocation and baseline outcome.",
         "Compare the candidate against the baseline using the same workload."),
    ),
    _Pattern(
        "information_bottleneck", "Information-bottleneck transfer",
        ("noise", "signal", "overload", "too much data", "retrieval", "search space"),
        "information theory", "search and decision systems", "information-flow graph",
        "Represent the pipeline as transformations and measure which stage preserves task-relevant information.",
        "Removing irrelevant variation can improve search only if task-relevant information is retained.",
        "A compressed or filtered representation should improve held-out task performance while preserving required facts.",
        "Held-out performance declines or a necessary fact is lost after the proposed compression/filtering.",
        ("Define task-relevant information in advance.", "Measure baseline recall and utility.",
         "Compare representations on held-out examples and adversarial cases."),
    ),
    _Pattern(
        "state_transition", "State-transition transfer",
        ("process", "workflow", "transition", "sequence", "state", "cycle"),
        "formal methods", "state machines and model checking", "state-transition graph",
        "Represent the process as states, transitions, invariants and explicit terminal conditions.",
        "A reachable state may violate an invariant even when each individual transition looks locally valid.",
        "Exhaustive or bounded state exploration should expose a counterexample if the transition system permits an invariant violation.",
        "Model checking the adequately specified state space finds no counterexample under the declared assumptions and bounds.",
        ("Enumerate states and valid transitions.", "Write invariants as executable predicates.",
         "Explore reachable states and retain any counterexample trace."),
    ),
)


def _compare(left: Scalar, operator: str, right: Scalar | None) -> bool:
    """Compare compatible scalar values using a closed operator set."""
    operations = {
        "eq": lambda: left == right,
        "ne": lambda: left != right,
        "lt": lambda: left < right,
        "le": lambda: left <= right,
        "gt": lambda: left > right,
        "ge": lambda: left >= right,
    }
    return bool(operations[operator]())


class DiscoveryEngine:
    """Generate testable structural transfers without disguising them as facts."""

    def analyze(
        self,
        question: str,
        claims: tuple[Claim, ...] = (),
        constraints: tuple[Constraint, ...] = (),
        values: dict[str, Scalar] | None = None,
        observations: tuple[Observation, ...] = (),
        max_hypotheses: int = 5,
    ) -> DiscoveryReport:
        """Analyze a problem and emit stable hypotheses and test instructions."""
        if not isinstance(question, str):
            raise ValueError("question must be a string")
        normalized = " ".join(question.split())
        if not normalized:
            raise ValueError("question must not be empty")
        if not 1 <= max_hypotheses <= 7:
            raise ValueError("max_hypotheses must be between 1 and 7")
        supplied_values = values or {}
        if any(not isinstance(v, (str, int, float, bool)) for v in supplied_values.values()):
            raise ValueError("values must be scalar JSON-compatible values")
        if any(isinstance(v, float) and not isfinite(v) for v in supplied_values.values()):
            raise ValueError("constraint numeric values must be finite")

        lowered = normalized.casefold()
        matched: list[tuple[_Pattern, tuple[str, ...]]] = []
        for pattern in _PATTERNS:
            terms = tuple(term for term in pattern.triggers if term in lowered)
            if terms:
                matched.append((pattern, terms))
        matched.sort(key=lambda item: (-len(item[1]), item[0].pattern_id))
        matched = matched[:max_hypotheses]

        hypotheses: list[Hypothesis] = []
        for pattern, terms in matched:
            hid = sha256(f"{normalized.casefold()}|{pattern.pattern_id}".encode()).hexdigest()[:16]
            related = tuple(item for item in observations if item.hypothesis_id == hid)
            support = tuple(item.observation_id for item in related if item.outcome == "supports")
            refute = tuple(item.observation_id for item in related if item.outcome == "refutes")
            if support and refute:
                status = HypothesisStatus.CONTESTED
            elif refute:
                status = HypothesisStatus.REFUTED
            elif support:
                status = HypothesisStatus.SUPPORTED
            elif any(item.outcome == "inconclusive" for item in related):
                status = HypothesisStatus.INCONCLUSIVE
            else:
                status = HypothesisStatus.CANDIDATE
            hypotheses.append(Hypothesis(
                hypothesis_id=hid, pattern_id=pattern.pattern_id, pattern_name=pattern.name,
                source_domain=pattern.source_domain, target_domain=pattern.target_domain,
                representation=pattern.representation, statement=pattern.statement,
                invariant=pattern.invariant, prediction=pattern.prediction, falsifier=pattern.falsifier,
                test_plan=pattern.tests, matched_terms=terms,
                match_strength=round(len(terms) / len(pattern.triggers), 3), status=status,
                supporting_observations=support, refuting_observations=refute,
            ))

        claims_by_key: dict[str, list[Claim]] = {}
        for claim in claims:
            if claim.proposition_key:
                claims_by_key.setdefault(claim.proposition_key, []).append(claim)
        contradictions: list[dict[str, str]] = []
        for key, group in sorted(claims_by_key.items()):
            positives = sorted((c for c in group if c.polarity), key=lambda c: c.claim_id)
            negatives = sorted((c for c in group if not c.polarity), key=lambda c: c.claim_id)
            for positive in positives:
                for negative in negatives:
                    contradictions.append({
                        "proposition_key": key, "claim_a": positive.claim_id,
                        "claim_b": negative.claim_id, "text_a": positive.text,
                        "text_b": negative.text, "status": "conflict_requires_resolution",
                    })

        constraint_results = tuple(c.evaluate(supplied_values) for c in constraints)
        hypothesis_ids = {h.hypothesis_id for h in hypotheses}
        unmatched = tuple(sorted(
            f"{item.observation_id}: no matching hypothesis id" for item in observations
            if item.hypothesis_id not in hypothesis_ids
        ))
        missing: list[str] = []
        if not claims:
            missing.append("No structured claims supplied; generated transfers rely only on the problem statement.")
        if not constraints:
            missing.append("No hard constraints supplied; feasibility cannot be fully assessed.")
        if constraints and not supplied_values:
            missing.append("No measured/current values supplied; constraints may remain unknown.")
        if not observations:
            missing.append("No observations supplied; generated hypotheses remain candidates.")
        if not matched:
            missing.append("No library pattern matched; clarify the question or add domain-specific patterns.")
        if any(c.evidence and not all(e.independently_checked for e in c.evidence) for c in claims):
            missing.append("At least one evidence item has not been independently checked by this engine.")
        identity = {
            "question": normalized, "claims": [asdict(c) for c in claims],
            "constraints": [asdict(c) for c in constraints], "values": supplied_values,
            "observations": [asdict(o) for o in observations], "max_hypotheses": max_hypotheses,
        }
        identity_json = json.dumps(identity, sort_keys=True, default=str, separators=(",", ":"))
        return DiscoveryReport(
            report_id=sha256(identity_json.encode()).hexdigest()[:24], question=normalized,
            representation_choices=tuple({
                "pattern_id": pattern.pattern_id, "representation": pattern.representation,
                "why": pattern.invariant,
            } for pattern, _ in matched),
            hypotheses=tuple(hypotheses), observations=observations,
            contradictions=tuple(contradictions),
            constraint_results=constraint_results, missing_information=tuple(missing),
            unmatched_observations=unmatched,
            limitations=(
                "Pattern matching is a deterministic heuristic, not a general scientific-discovery algorithm.",
                "Contradictions require a shared, correctly assigned proposition_key and opposite polarity.",
                "Reported observations are not independently authenticated or reproduced by this module.",
                "Novelty and prior art have not been checked.",
                "Empirical truth requires domain-specific evidence, tests, and independent review.",
                "A satisfied constraint verifies only the declared condition against supplied values.",
            ),
        )
