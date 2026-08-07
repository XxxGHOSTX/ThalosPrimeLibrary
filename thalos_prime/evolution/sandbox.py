"""Deterministic benchmark/sandbox abstraction for candidate evaluation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    input: Any
    expected: Any


@dataclass
class BenchmarkResult:
    candidate_id: str
    accuracy: float
    latency_score: float
    efficiency_score: float
    passed: bool
    cases: int
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def fitness(self) -> float:
        return 0.6 * self.accuracy + 0.25 * self.latency_score + 0.15 * self.efficiency_score


@dataclass
class BenchmarkSuite:
    cases: list[BenchmarkCase]
    evaluator: Callable[[Any, Any], bool]


class SandboxEvaluator:
    """Evaluates candidates without mutating the active runtime."""

    def evaluate(self, candidate_id: str, candidate: Callable[[Any], Any], suite: BenchmarkSuite) -> BenchmarkResult:
        passed = 0
        failures: list[str] = []
        for case in suite.cases:
            try:
                actual = candidate(case.input)
                if suite.evaluator(actual, case.expected):
                    passed += 1
                else:
                    failures.append(case.case_id)
            except Exception as exc:
                failures.append(f"{case.case_id}:{type(exc).__name__}")
        total = len(suite.cases)
        accuracy = passed / total if total else 0.0
        return BenchmarkResult(
            candidate_id=candidate_id, accuracy=accuracy,
            latency_score=1.0, efficiency_score=1.0,
            passed=not failures and bool(total), cases=total,
            details={"failed_cases": failures},
        )
