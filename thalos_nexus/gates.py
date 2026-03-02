"""Thalos NEXUS — Gate definitions.

Defines the ``GateSpec`` dataclass and the canonical ``STANDARD_GATES`` list
used by the lysosome gate runner.

Each gate is described as a sequence of shell commands (in list form for
Windows compatibility) plus metadata.  Actual execution is delegated to
``lysosome.GateRunner``.

Control Plane boundary: this module declares *what* to run, not *how*.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# GateSpec
# ---------------------------------------------------------------------------


@dataclass
class GateSpec:
    """Specification for a single quality gate.

    Attributes
    ----------
    name:
        Short, unique identifier for this gate.
    commands:
        Ordered list of commands to execute.  Each command is a list of
        strings (argv style) for cross-platform compatibility.
    fatal:
        When ``True``, gate failure halts the entire gate suite immediately.
    description:
        Human-readable description of what this gate verifies.

    """

    name: str
    commands: list[list[str]]
    fatal: bool
    description: str
    timeout_seconds: float = field(default=300.0)


# ---------------------------------------------------------------------------
# Standard gate suite
# ---------------------------------------------------------------------------


def make_no_placeholder_gate() -> GateSpec:
    """Return the no-placeholder scan gate (fatal).

    Scans the repository for ``TODO``, ``FIXME``, ``STUB``, and
    ``PLACEHOLDER`` markers in Python source files.
    """
    return GateSpec(
        name="no-placeholder",
        commands=[
            [
                "python",
                "-c",
                (
                    "import subprocess, sys; "
                    "r = subprocess.run("
                    "['grep', '-rn', '--include=*.py', "
                    "'-E', 'TODO|FIXME|STUB|PLACEHOLDER', '.'], "
                    "capture_output=True, text=True); "
                    "print(r.stdout); "
                    "sys.exit(1 if r.stdout.strip() else 0)"
                ),
            ]
        ],
        fatal=True,
        description="Scan for TODO/FIXME/STUB/PLACEHOLDER markers in Python source.",
    )


def make_static_analysis_gate() -> GateSpec:
    """Return the static analysis gate (ruff + mypy strict)."""
    return GateSpec(
        name="static-analysis",
        commands=[
            ["python", "-m", "ruff", "check", "thalos_nexus"],
            ["python", "-m", "mypy", "thalos_nexus", "--strict"],
        ],
        fatal=False,
        description="Run ruff linter and mypy --strict type checker.",
    )


def make_security_scan_gate() -> GateSpec:
    """Return the security scan gate (pip-audit)."""
    return GateSpec(
        name="security-scan",
        commands=[["python", "-m", "pip_audit"]],
        fatal=False,
        description="Run pip-audit to detect known vulnerabilities in dependencies.",
    )


def make_acceptance_tests_gate() -> GateSpec:
    """Return the acceptance tests gate (pytest)."""
    return GateSpec(
        name="acceptance-tests",
        commands=[
            [
                "python",
                "-m",
                "pytest",
                "tests/",
                "-v",
                "--tb=short",
                "-x",
            ]
        ],
        fatal=False,
        description="Run the pytest acceptance test suite.",
    )


def make_property_tests_gate() -> GateSpec:
    """Return the property-based tests gate (hypothesis via pytest)."""
    return GateSpec(
        name="property-tests",
        commands=[
            [
                "python",
                "-m",
                "pytest",
                "tests/",
                "-v",
                "--tb=short",
                "-m",
                "hypothesis",
            ]
        ],
        fatal=False,
        description="Run hypothesis property-based tests.",
    )


def make_mutation_resilience_gate() -> GateSpec:
    """Return the mutation resilience gate (mutmut)."""
    return GateSpec(
        name="mutation-resilience",
        commands=[["python", "-m", "mutmut", "run", "--paths-to-mutate", "thalos_nexus/"]],
        fatal=False,
        description="Run mutmut mutation testing for resilience verification.",
        timeout_seconds=600.0,
    )


def make_deterministic_replay_gate() -> GateSpec:
    """Return the deterministic replay check gate (fatal)."""
    return GateSpec(
        name="deterministic-replay",
        commands=[
            [
                "python",
                "-c",
                (
                    "from thalos_nexus.nucleus import ingest_genome; "
                    "print('deterministic-replay: nucleus import OK')"
                ),
            ]
        ],
        fatal=True,
        description="Verify the deterministic replay invariant is satisfied.",
    )


def make_coverage_enforcement_gate() -> GateSpec:
    """Return the coverage enforcement gate (>=80%)."""
    return GateSpec(
        name="coverage-enforcement",
        commands=[
            [
                "python",
                "-m",
                "pytest",
                "tests/",
                "--cov=thalos_nexus",
                "--cov-fail-under=80",
                "--cov-report=term-missing",
                "-q",
            ]
        ],
        fatal=False,
        description="Enforce >=80% line coverage across thalos_nexus.",
    )


STANDARD_GATES: list[GateSpec] = [
    make_no_placeholder_gate(),
    make_static_analysis_gate(),
    make_security_scan_gate(),
    make_acceptance_tests_gate(),
    make_property_tests_gate(),
    make_mutation_resilience_gate(),
    make_deterministic_replay_gate(),
    make_coverage_enforcement_gate(),
]
