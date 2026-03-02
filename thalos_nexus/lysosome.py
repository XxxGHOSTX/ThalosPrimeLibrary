"""Thalos NEXUS — Lysosome: deterministic gate runner.

Executes a sequence of ``GateSpec`` objects in order, collecting results.
Each gate command is run via ``subprocess.run`` with a configurable timeout,
making the runner compatible with Windows 10 Home.

"Windows isolation adapter" is implemented as subprocess isolation: each gate
command runs in its own subprocess, fully isolated from the parent process.

Control Plane boundary: this module runs gates and records results; it does
not decide which gates to run or how to interpret failures at the policy level.

Determinism note:
    Gate pass/fail decisions are based solely on subprocess exit codes, which
    are deterministic given identical input code.  Duration measurements
    (``duration_seconds``) use ``time.monotonic()`` and are observability
    metadata only — they never affect gate pass/fail status or execution order.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from thalos_nexus.gates import GateSpec

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class GateResult:
    """Result of executing a single gate.

    Attributes
    ----------
    gate_name:
        Name of the gate that was executed.
    passed:
        ``True`` if all commands in the gate exited with code 0.
    exit_code:
        Exit code of the last command executed (or first failing command).
    stdout:
        Combined stdout from all commands in the gate.
    stderr:
        Combined stderr from all commands in the gate.
    duration_seconds:
        Wall-clock execution time for the gate.
    fatal:
        Mirrors ``GateSpec.fatal`` for downstream consumers.

    """

    gate_name: str
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    fatal: bool

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dictionary (gate_results schema compatible)."""
        return {
            "name": self.gate_name,
            "passed": self.passed,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "fatal": self.fatal,
        }


@dataclass
class GateRunResults:
    """Aggregated results from a full gate suite run.

    Attributes
    ----------
    all_passed:
        ``True`` only if every gate passed.
    results:
        Ordered list of individual gate results.
    total_duration:
        Sum of all gate durations in seconds.

    """

    all_passed: bool
    results: list[GateResult]
    total_duration: float = field(default=0.0)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dictionary (gate_results schema compatible)."""
        return {
            "schema_version": "1.0",
            "all_passed": self.all_passed,
            "total_duration_seconds": self.total_duration,
            "gates": [r.to_dict() for r in self.results],
        }


# ---------------------------------------------------------------------------
# GateRunner
# ---------------------------------------------------------------------------


class GateRunner:
    """Runs a list of gates sequentially, collecting results.

    Parameters
    ----------
    gates:
        Ordered list of gate specifications to execute.
    cwd:
        Working directory for subprocess execution.  Defaults to the current
        working directory.
    default_timeout:
        Per-gate timeout in seconds (overridden by ``GateSpec.timeout_seconds``
        when provided).

    """

    def __init__(
        self,
        gates: list[GateSpec],
        cwd: str | None = None,
        default_timeout: float = 300.0,
    ) -> None:
        """Initialise the runner with a gate list and working directory."""
        self._gates = gates
        self._cwd = cwd
        self._default_timeout = default_timeout

    def run(self) -> GateRunResults:
        """Execute all gates in order and return the aggregated results.

        Execution stops immediately after any gate whose ``fatal`` flag is set
        and which has failed.

        Returns
        -------
        GateRunResults
            Aggregated pass/fail status and per-gate details.

        """
        results: list[GateResult] = []
        all_passed = True
        suite_start = time.monotonic()

        for gate_spec in self._gates:
            result = self._run_gate(gate_spec)
            results.append(result)
            if not result.passed:
                all_passed = False
                if gate_spec.fatal:
                    break

        total_duration = time.monotonic() - suite_start
        return GateRunResults(
            all_passed=all_passed,
            results=results,
            total_duration=total_duration,
        )

    def _run_gate(self, gate_spec: GateSpec) -> GateResult:
        """Execute a single gate, running its commands in sequence.

        Parameters
        ----------
        gate_spec:
            The gate to run.

        Returns
        -------
        GateResult
            Execution result for this gate.

        """
        gate_start = time.monotonic()
        combined_stdout: list[str] = []
        combined_stderr: list[str] = []
        last_exit_code = 0
        passed = True
        timeout = gate_spec.timeout_seconds

        for cmd in gate_spec.commands:
            try:
                proc = subprocess.run(  # noqa: S603
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=self._cwd,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                duration = time.monotonic() - gate_start
                stdout_so_far = exc.stdout if isinstance(exc.stdout, str) else ""
                stderr_so_far = exc.stderr if isinstance(exc.stderr, str) else ""
                return GateResult(
                    gate_name=gate_spec.name,
                    passed=False,
                    exit_code=124,
                    stdout=stdout_so_far,
                    stderr=f"TIMEOUT after {timeout}s\n{stderr_so_far}",
                    duration_seconds=duration,
                    fatal=gate_spec.fatal,
                )
            combined_stdout.append(proc.stdout or "")
            combined_stderr.append(proc.stderr or "")
            last_exit_code = proc.returncode
            if proc.returncode != 0:
                passed = False
                break

        duration = time.monotonic() - gate_start
        return GateResult(
            gate_name=gate_spec.name,
            passed=passed,
            exit_code=last_exit_code,
            stdout="".join(combined_stdout),
            stderr="".join(combined_stderr),
            duration_seconds=duration,
            fatal=gate_spec.fatal,
        )
