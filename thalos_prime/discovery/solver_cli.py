"""Command-line interface for the adaptive finite-domain solver."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from thalos_prime.discovery.representation_search import (
    AdaptiveRepresentationEngine,
    FiniteDomainProblem,
    RelationConstraint,
    VariableDomain,
)


def main(argv: list[str] | None = None) -> int:
    """Read a finite-domain problem JSON file and emit a verification report."""
    parser = argparse.ArgumentParser(
        prog="thalos-solve",
        description="Select a finite-domain representation and test feasibility.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Problem specification JSON")
    parser.add_argument("--output", type=Path, help="Write report JSON to this file")
    args = parser.parse_args(argv)
    try:
        payload: Any = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or "problem_id" not in payload:
            msg = "input JSON must be an object with problem_id"
            raise ValueError(msg)
        variables = tuple(
            VariableDomain(item["name"], tuple(item["domain"]))
            for item in payload["variables"]
        )
        constraints = tuple(
            RelationConstraint(**item) for item in payload.get("constraints", [])
        )
        problem = FiniteDomainProblem(str(payload["problem_id"]), variables, constraints)
        report = AdaptiveRepresentationEngine().solve(problem)
        rendered = json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
        if args.output is not None:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"thalos-solve: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
