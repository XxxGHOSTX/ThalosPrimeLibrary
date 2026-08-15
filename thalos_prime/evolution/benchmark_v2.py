"""Repeated statistical benchmark execution for evolution candidates."""
from __future__ import annotations

from dataclasses import dataclass, field
import statistics
import time
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class TrialSample:
    case_id: str
    duration_ns: int
    passed: bool
    error: str | None = None


@dataclass(frozen=True)
class StatisticalBenchmarkResult:
    candidate_id: str
    trials: tuple[TrialSample, ...]
    warmups: int
    repeats: int
    accuracy: float
    median_latency_ns: float
    p95_latency_ns: float
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def latency_score(self) -> float:
        if self.median_latency_ns <= 0:
            return 0.0
        return 1.0 / self.median_latency_ns


class RepeatedBenchmark:
    """Runs the same deterministic cases repeatedly and records latency."""

    def __init__(self, warmups: int = 1, repeats: int = 3) -> None:
        if warmups < 0 or repeats < 1:
            raise ValueError("warmups must be >= 0 and repeats must be >= 1")
        self.warmups = warmups
        self.repeats = repeats

    def evaluate(
        self,
        candidate_id: str,
        candidate: Callable[[Any], Any],
        cases: Sequence[tuple[str, Any, Any]],
        evaluator: Callable[[Any, Any], bool],
    ) -> StatisticalBenchmarkResult:
        samples: list[TrialSample] = []
        for case_id, value, expected in cases:
            for _ in range(self.warmups):
                candidate(value)
            for _ in range(self.repeats):
                started = time.perf_counter_ns()
                try:
                    actual = candidate(value)
                    passed = bool(evaluator(actual, expected))
                    error = None
                except Exception as exc:  # candidate failures are benchmark evidence
                    passed = False
                    error = f"{type(exc).__name__}: {exc}"
                samples.append(
                    TrialSample(
                        case_id=case_id,
                        duration_ns=time.perf_counter_ns() - started,
                        passed=passed,
                        error=error,
                    )
                )
        latencies = [sample.duration_ns for sample in samples]
        passed_count = sum(sample.passed for sample in samples)
        accuracy = passed_count / len(samples) if samples else 0.0
        ordered = sorted(latencies)
        p95_index = max(0, min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1)))) if ordered else 0)
        median = statistics.median(ordered) if ordered else 0.0
        p95 = float(ordered[p95_index]) if ordered else 0.0
        return StatisticalBenchmarkResult(
            candidate_id=candidate_id,
            trials=tuple(samples),
            warmups=self.warmups,
            repeats=self.repeats,
            accuracy=accuracy,
            median_latency_ns=float(median),
            p95_latency_ns=p95,
            passed=bool(samples) and all(sample.passed for sample in samples),
            details={"failed_cases": sorted({s.case_id for s in samples if not s.passed})},
        )
