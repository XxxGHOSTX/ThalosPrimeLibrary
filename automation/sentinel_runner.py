"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.

Entry point for automated Sentinel scan (used by GitHub Actions).
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.discovery_sentinel.scanner import SentinelScanner  # noqa: E402
from services.discovery_sentinel.risk_analyzer import RiskAnalyzer  # noqa: E402
from core.utilities import append_jsonl, now_iso, compute_sha256, validate_seed  # noqa: E402


def run_scan(seed: int | None, log_file: str | None = None) -> int:
    """Run the sentinel scan. Requires a valid 64-bit seed; returns exit code."""
    if seed is None:
        print(
            "ERROR: --seed is required. Per governance, every service generating output MUST receive a seed.",
            file=sys.stderr,
        )
        return 1
    try:
        actual_seed = validate_seed(seed)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    scanner = SentinelScanner()
    log_entries = []
    if log_file and Path(log_file).exists():
        log_entries = Path(log_file).read_text().splitlines()

    findings = scanner.audit_bulk(log_entries)
    analyzer = RiskAnalyzer()
    report = analyzer.analyze(findings)

    event = {
        "runner": "sentinel_runner",
        "seed": actual_seed,
        "findings_count": len(findings),
        "risk_level": report.risk_level,
        "risk_score": report.total_score,
        "state_hash": compute_sha256({"seed": actual_seed, "findings": findings}),
        "timestamp": now_iso(),
    }
    append_jsonl("STATELOG/discovery.jsonl", event)
    print(
        f"Scan complete. Findings: {len(findings)} | "
        f"Risk: {report.risk_level} | Hash: {event['state_hash']}"
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ThalosPrime Sentinel Runner")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--log-file", default=None)
    args = parser.parse_args()
    sys.exit(run_scan(args.seed, args.log_file))
