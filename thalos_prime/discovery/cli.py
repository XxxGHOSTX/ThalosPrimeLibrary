"""Command-line interface for Thalos Prime's falsifiable discovery engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from thalos_prime.discovery.engine import (
    Claim,
    Constraint,
    DiscoveryEngine,
    Evidence,
    Observation,
)


def _construct_input(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert JSON-compatible input sections into typed domain objects."""
    parsed_claims: list[Claim] = []
    for raw_claim in payload.get("claims", []):
        claim_data = dict(raw_claim)
        claim_data["assumptions"] = tuple(claim_data.get("assumptions", ()))
        claim_data["evidence"] = tuple(
            Evidence(**item) for item in claim_data.get("evidence", ())
        )
        parsed_claims.append(Claim(**claim_data))

    constraints = tuple(Constraint(**item) for item in payload.get("constraints", []))
    observations = tuple(Observation(**item) for item in payload.get("observations", []))
    values = payload.get("values")
    if values is not None and not isinstance(values, dict):
        raise ValueError("values must be a JSON object")
    return {
        "question": payload["question"],
        "claims": tuple(parsed_claims),
        "constraints": constraints,
        "values": values,
        "observations": observations,
        "max_hypotheses": int(payload.get("max_hypotheses", 5)),
    }


def main(argv: list[str] | None = None) -> int:
    """Run analysis from a question string or a structured JSON problem file."""
    parser = argparse.ArgumentParser(
        prog="thalos-discover",
        description="Generate falsifiable cross-domain hypotheses and constraint reports.",
    )
    parser.add_argument("question", nargs="*", help="Problem statement (not used with --input)")
    parser.add_argument(
        "--input",
        type=Path,
        help="JSON file with question, claims, constraints, values, and observations",
    )
    parser.add_argument("--output", type=Path, help="Write report JSON to a file instead of stdout")
    parser.add_argument("--max-hypotheses", type=int, default=5)
    args = parser.parse_args(argv)

    try:
        if args.input is not None:
            payload = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or "question" not in payload:
                raise ValueError("input JSON must be an object containing a question field")
            call_args = _construct_input(payload)
        else:
            question = " ".join(args.question).strip()
            if not question:
                raise ValueError("provide a question or --input JSON file")
            call_args = {"question": question, "max_hypotheses": args.max_hypotheses}
        report = DiscoveryEngine().analyze(**call_args)
        rendered = json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
        if args.output is not None:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"thalos-discover: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
