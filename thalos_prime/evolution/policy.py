"""Policy gates for autonomous repository evolution.

The policy layer is deliberately conservative: it constrains what an autonomous
run may propose and what may be promoted, without pretending that a textual
filter is a complete security boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import PurePosixPath
from typing import Iterable


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reasons: tuple[str, ...] = ()

    def require_allowed(self) -> None:
        if not self.allowed:
            raise PermissionError("; ".join(self.reasons))


@dataclass(frozen=True)
class EvolutionPolicy:
    """Repository-level constraints for autonomous changes."""

    allowed_paths: tuple[str, ...] = (
        "thalos_prime/**",
        "tests/**",
        "docs/**",
    )
    denied_paths: tuple[str, ...] = (
        ".github/workflows/**",
        ".github/actions/**",
        ".env",
        ".env.*",
        "**/secrets/**",
    )
    max_changed_files: int = 8
    max_added_lines: int = 1200
    max_deleted_lines: int = 1200
    max_patch_bytes: int = 250_000
    forbidden_tokens: tuple[str, ...] = (
        "BEGIN OPENSSH PRIVATE KEY",
        "BEGIN PRIVATE KEY",
        "gh auth login",
        "curl | sh",
        "wget | sh",
        "rm -rf /",
        "os.system(",
        "subprocess.Popen(",
    )
    min_accuracy: float = 1.0
    min_relative_improvement: float = 0.01
    max_relative_regression: float = 0.0
    auto_promote: bool = False
    require_tests: bool = True
    require_benchmark: bool = True

    def check_paths(self, paths: Iterable[str]) -> PolicyDecision:
        normalized = [PurePosixPath(path).as_posix() for path in paths]
        reasons: list[str] = []
        if len(normalized) > self.max_changed_files:
            reasons.append(
                f"changed file count {len(normalized)} exceeds {self.max_changed_files}"
            )
        for path in normalized:
            if any(fnmatch(path, pattern) for pattern in self.denied_paths):
                reasons.append(f"denied path: {path}")
                continue
            if not any(fnmatch(path, pattern) for pattern in self.allowed_paths):
                reasons.append(f"path outside allowlist: {path}")
        return PolicyDecision(not reasons, tuple(reasons))

    def check_diff(self, diff_text: str) -> PolicyDecision:
        reasons: list[str] = []
        raw_size = len(diff_text.encode("utf-8"))
        if raw_size > self.max_patch_bytes:
            reasons.append(f"patch size {raw_size} exceeds {self.max_patch_bytes} bytes")

        additions = 0
        deletions = 0
        for line in diff_text.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                additions += 1
            elif line.startswith("-"):
                deletions += 1
        if additions > self.max_added_lines:
            reasons.append(f"added lines {additions} exceeds {self.max_added_lines}")
        if deletions > self.max_deleted_lines:
            reasons.append(f"deleted lines {deletions} exceeds {self.max_deleted_lines}")

        lowered = diff_text.lower()
        for token in self.forbidden_tokens:
            if token.lower() in lowered:
                reasons.append(f"forbidden token detected: {token}")
        return PolicyDecision(not reasons, tuple(reasons))

    def check_metrics(
        self,
        baseline_accuracy: float,
        candidate_accuracy: float,
        baseline_latency: float,
        candidate_latency: float,
    ) -> PolicyDecision:
        reasons: list[str] = []
        if candidate_accuracy < self.min_accuracy:
            reasons.append(
                f"candidate accuracy {candidate_accuracy:.6f} is below {self.min_accuracy:.6f}"
            )
        if baseline_accuracy > 0.0:
            accuracy_delta = (candidate_accuracy - baseline_accuracy) / baseline_accuracy
            if accuracy_delta < 0.0:
                reasons.append(f"accuracy regression {accuracy_delta:.6%}")
        if baseline_latency > 0.0:
            latency_delta = (candidate_latency - baseline_latency) / baseline_latency
            if latency_delta > self.max_relative_regression:
                if latency_delta > -self.min_relative_improvement:
                    reasons.append(f"latency regression {latency_delta:.6%}")
        return PolicyDecision(not reasons, tuple(reasons))

    def can_activate(
        self,
        *,
        tests_passed: bool,
        benchmark_passed: bool,
        relative_improvement: float,
    ) -> PolicyDecision:
        reasons: list[str] = []
        if self.require_tests and not tests_passed:
            reasons.append("required tests did not pass")
        if self.require_benchmark and not benchmark_passed:
            reasons.append("required benchmark did not pass")
        if relative_improvement < self.min_relative_improvement:
            reasons.append(
                f"improvement {relative_improvement:.6%} is below "
                f"{self.min_relative_improvement:.6%}"
            )
        return PolicyDecision(not reasons, tuple(reasons))
