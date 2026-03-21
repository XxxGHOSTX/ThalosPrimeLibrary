"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

import sys
import argparse

from core.utilities import compute_sha256, append_jsonl, now_iso, validate_seed


class ThalosOrchestrator:
    """
    Controls the Thalos Prime execution pipeline.
    Coordinates discovery → risk analysis → artifact generation.
    """

    def __init__(self, seed: int, statelog_path: str = "STATELOG/events.jsonl") -> None:
        """Initialize the orchestrator with a validated seed.

        Args:
            seed: 64-bit execution seed.
            statelog_path: Path to write STATELOG events.

        Raises:
            ValueError: If seed is invalid.
        """
        self.seed = validate_seed(seed)
        self.statelog_path = statelog_path

    def run_discovery_pipeline(self, log_entries: list[str]) -> dict:
        """Run the full discovery-to-remediation pipeline.

        Args:
            log_entries: Network log lines to scan.

        Returns:
            dict with findings, risk_level, risk_score, and state_hash.
        """
        from services.discovery_sentinel.scanner import SentinelScanner
        from services.discovery_sentinel.risk_analyzer import RiskAnalyzer

        scanner = SentinelScanner()
        findings = scanner.audit_bulk(log_entries)

        analyzer = RiskAnalyzer()
        report = analyzer.analyze(findings)

        event = {
            "pipeline": "discovery",
            "seed": self.seed,
            "findings_count": len(findings),
            "risk_level": report.risk_level,
            "risk_score": report.total_score,
            "state_hash": compute_sha256({"seed": self.seed, "findings": findings}),
            "timestamp": now_iso(),
        }
        append_jsonl(self.statelog_path, event)

        return {
            "findings": report.findings,
            "risk_level": report.risk_level,
            "risk_score": report.total_score,
            "state_hash": event["state_hash"],
        }

    def _log_event(self, event_type: str, payload: dict) -> None:
        """Log a lifecycle event to the STATELOG."""
        record = {
            "event_type": event_type,
            "seed": self.seed,
            "payload": payload,
            "state_hash": compute_sha256(payload),
            "timestamp": now_iso(),
        }
        append_jsonl(self.statelog_path, record)


def main() -> None:
    """CLI entry point for the Thalos Prime Orchestrator."""
    parser = argparse.ArgumentParser(description="Thalos Prime Orchestrator")
    parser.add_argument("--seed", type=int, required=True, help="64-bit execution seed (required)")
    parser.add_argument("--log-file", type=str, default=None, help="Path to network log file to scan")
    args = parser.parse_args()

    try:
        validate_seed(args.seed)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    orchestrator = ThalosOrchestrator(seed=args.seed)

    log_entries: list[str] = []
    if args.log_file:
        with open(args.log_file, encoding="utf-8") as f:
            log_entries = f.readlines()

    result = orchestrator.run_discovery_pipeline(log_entries)
    print(f"Pipeline complete. Risk: {result['risk_level']} | Hash: {result['state_hash']}")


if __name__ == "__main__":
    main()
