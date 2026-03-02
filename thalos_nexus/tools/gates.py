"""Thalos Prime NEXUS Core v1 — Hard Gate Definitions.

Defines :class:`GateContext`, :class:`GateResult`, and all six hard gates
that must pass before a NEXUS evolution run is accepted.  Also provides
:class:`GateRunner` which orchestrates gate execution.

Control Plane boundary: subprocess execution and result collection only.
No lifecycle coordination logic belongs here.
"""

from __future__ import annotations

import logging
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

logger = logging.getLogger(__name__)


@dataclass
class GateContext:
    """Context passed to every gate function."""

    run_id: str
    target_dir: Path
    workspace_dir: Path
    python_executable: str
    timeout_seconds: float = 300.0


@dataclass
class GateResult:
    """Result produced by a single gate execution."""

    name: str
    passed: bool
    duration_seconds: float
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    error: str | None = field(default=None)


def _run_command(
    cmd: list[str],
    cwd: Path,
    timeout: float,
) -> tuple[int, str, str]:
    """Execute *cmd* in *cwd* and capture output.

    Args:
        cmd: Command and arguments.
        cwd: Working directory for the subprocess.
        timeout: Maximum execution time in seconds.

    Returns:
        Tuple of (returncode, stdout, stderr).

    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return (
            result.returncode,
            result.stdout.decode(errors="replace"),
            result.stderr.decode(errors="replace"),
        )
    except subprocess.TimeoutExpired as exc:
        stderr_partial = (exc.stderr or b"").decode(errors="replace")
        return 1, "", f"Timeout after {timeout}s\n{stderr_partial}"
    except OSError as exc:
        return 1, "", str(exc)


def run_no_placeholder_gate(ctx: GateContext) -> GateResult:
    """Gate: reject any .py file containing TODO/FIXME/STUB/HACK/TBD/PLACEHOLDER.

    Scans all ``.py`` files under ``ctx.target_dir`` for forbidden keywords.
    Passes if no matches are found.

    Args:
        ctx: Gate execution context.

    Returns:
        :class:`GateResult` with passed=True if no forbidden keywords found.

    """
    name = "no_placeholder"
    forbidden = ("TODO", "FIXME", "STUB", "HACK", "TBD", "PLACEHOLDER")
    matches: list[str] = []

    try:
        for py_file in sorted(ctx.target_dir.rglob("*.py")):
            try:
                text = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                matches.extend(
                        f"{py_file}:{lineno}: {line.strip()}"
                        for kw in forbidden
                        if kw in line
                    )
    except OSError as exc:
        return GateResult(
            name=name,
            passed=False,
            duration_seconds=0.0,
            exit_code=1,
            error=str(exc),
        )

    if matches:
        return GateResult(
            name=name,
            passed=False,
            duration_seconds=0.0,
            exit_code=1,
            stderr="\n".join(matches),
        )
    return GateResult(name=name, passed=True, duration_seconds=0.0, exit_code=0)


def run_static_analysis_gate(ctx: GateContext) -> GateResult:
    """Gate: run ruff and mypy --strict on the target directory.

    Both tools must exit 0 for the gate to pass.  ruff runs first; mypy
    is skipped if ruff fails to keep output focused.

    Args:
        ctx: Gate execution context.

    Returns:
        :class:`GateResult` reflecting combined ruff + mypy outcome.

    """
    name = "static_analysis"
    start = time.monotonic()

    ruff_rc, ruff_out, ruff_err = _run_command(
        ["ruff", "check", str(ctx.target_dir)],
        ctx.target_dir,
        ctx.timeout_seconds,
    )

    mypy_rc, mypy_out, mypy_err = _run_command(
        [ctx.python_executable, "-m", "mypy", str(ctx.target_dir), "--strict"],
        ctx.target_dir,
        ctx.timeout_seconds,
    )

    duration = time.monotonic() - start
    combined_stdout = f"=== ruff ===\n{ruff_out}\n=== mypy ===\n{mypy_out}"
    combined_stderr = f"=== ruff ===\n{ruff_err}\n=== mypy ===\n{mypy_err}"
    passed = ruff_rc == 0 and mypy_rc == 0
    exit_code = ruff_rc if ruff_rc != 0 else mypy_rc

    return GateResult(
        name=name,
        passed=passed,
        duration_seconds=duration,
        exit_code=exit_code,
        stdout=combined_stdout,
        stderr=combined_stderr,
    )


def run_security_gate(ctx: GateContext) -> GateResult:
    """Gate: run pip-audit to check for known vulnerabilities.

    Args:
        ctx: Gate execution context.

    Returns:
        :class:`GateResult` reflecting pip-audit outcome.

    """
    name = "security"
    start = time.monotonic()
    rc, out, err = _run_command(
        [ctx.python_executable, "-m", "pip_audit"],
        ctx.target_dir,
        ctx.timeout_seconds,
    )
    duration = time.monotonic() - start
    return GateResult(
        name=name,
        passed=rc == 0,
        duration_seconds=duration,
        exit_code=rc,
        stdout=out,
        stderr=err,
    )


def run_acceptance_tests_gate(ctx: GateContext) -> GateResult:
    """Gate: run the full pytest suite for the target directory.

    Args:
        ctx: Gate execution context.

    Returns:
        :class:`GateResult` reflecting pytest outcome.

    """
    name = "acceptance_tests"
    start = time.monotonic()
    rc, out, err = _run_command(
        [ctx.python_executable, "-m", "pytest", str(ctx.target_dir), "-v"],
        ctx.target_dir,
        ctx.timeout_seconds,
    )
    duration = time.monotonic() - start
    return GateResult(
        name=name,
        passed=rc == 0,
        duration_seconds=duration,
        exit_code=rc,
        stdout=out,
        stderr=err,
    )


def run_property_tests_gate(ctx: GateContext) -> GateResult:
    """Gate: run property-based (Hypothesis) tests for the target directory.

    Executes ``pytest -k hypothesis`` to select only Hypothesis tests.

    Args:
        ctx: Gate execution context.

    Returns:
        :class:`GateResult` reflecting pytest outcome for Hypothesis tests.

    """
    name = "property_tests"
    start = time.monotonic()
    rc, out, err = _run_command(
        [
            ctx.python_executable,
            "-m",
            "pytest",
            str(ctx.target_dir),
            "-k",
            "hypothesis",
            "-v",
        ],
        ctx.target_dir,
        ctx.timeout_seconds,
    )
    duration = time.monotonic() - start
    return GateResult(
        name=name,
        passed=rc == 0,
        duration_seconds=duration,
        exit_code=rc,
        stdout=out,
        stderr=err,
    )


def run_mutation_tests_gate(ctx: GateContext) -> GateResult:
    """Gate: run mutmut mutation tests on the target directory.

    Runs ``mutmut run`` followed by ``mutmut results``.  The gate passes only
    when mutmut exits 0 on both invocations (meaning no surviving mutants).

    Args:
        ctx: Gate execution context.

    Returns:
        :class:`GateResult` reflecting combined mutmut outcome.

    """
    name = "mutation_tests"
    start = time.monotonic()

    run_rc, run_out, run_err = _run_command(
        [
            ctx.python_executable,
            "-m",
            "mutmut",
            "run",
            "--paths-to-mutate",
            str(ctx.target_dir),
        ],
        ctx.target_dir,
        ctx.timeout_seconds,
    )

    results_rc, results_out, results_err = _run_command(
        [ctx.python_executable, "-m", "mutmut", "results"],
        ctx.target_dir,
        ctx.timeout_seconds,
    )

    duration = time.monotonic() - start
    combined_stdout = f"=== mutmut run ===\n{run_out}\n=== mutmut results ===\n{results_out}"
    combined_stderr = f"=== mutmut run ===\n{run_err}\n=== mutmut results ===\n{results_err}"
    passed = run_rc == 0 and results_rc == 0
    exit_code = run_rc if run_rc != 0 else results_rc

    return GateResult(
        name=name,
        passed=passed,
        duration_seconds=duration,
        exit_code=exit_code,
        stdout=combined_stdout,
        stderr=combined_stderr,
    )


class GateRunner:
    """Orchestrates execution of all hard gates for a NEXUS run.

    Args:
        ctx: Gate context shared across all gates.

    """

    _ALL_GATES: ClassVar[list[Callable[[GateContext], GateResult]]] = [
        run_no_placeholder_gate,
        run_static_analysis_gate,
        run_security_gate,
        run_acceptance_tests_gate,
        run_property_tests_gate,
        run_mutation_tests_gate,
    ]

    def __init__(self, ctx: GateContext) -> None:
        """Initialise the runner with *ctx*."""
        self._ctx = ctx

    def run_all(self) -> list[GateResult]:
        """Run all six gates in order and collect results.

        All gates are executed regardless of individual pass/fail status so
        that the full picture is captured in the run artifacts.

        Returns:
            Ordered list of :class:`GateResult` objects.

        """
        results: list[GateResult] = []
        for gate_fn in self._ALL_GATES:
            result = self.run_gate(gate_fn)
            results.append(result)
            status = "PASS" if result.passed else "FAIL"
            logger.info("Gate %s: %s (%.2fs)", result.name, status, result.duration_seconds)
        return results

    def run_gate(self, gate_fn: Callable[[GateContext], GateResult]) -> GateResult:
        """Execute a single *gate_fn* with timing.

        Args:
            gate_fn: Gate callable accepting :class:`GateContext`.

        Returns:
            :class:`GateResult` produced by the gate.

        """
        start = time.monotonic()
        result = gate_fn(self._ctx)
        if result.duration_seconds == 0.0:
            result.duration_seconds = time.monotonic() - start
        return result
