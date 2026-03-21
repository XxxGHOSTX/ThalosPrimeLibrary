"""Tests for platform services: SentinelScanner, RiskAnalyzer, and ThalosOrchestrator.

Covers seed validation, scanner findings, risk scoring, and pipeline STATELOG output.
"""

import json
from pathlib import Path

import pytest

from services.discovery_sentinel.scanner import SentinelScanner
from services.discovery_sentinel.risk_analyzer import RiskAnalyzer


# ---------------------------------------------------------------------------
# SentinelScanner
# ---------------------------------------------------------------------------


def test_scanner_detects_openai_egress() -> None:
    """audit_traffic detects unauthorized calls to api.openai.com."""
    scanner = SentinelScanner()
    result = scanner.audit_traffic("GET https://api.openai.com/v1/chat/completions HTTP/1.1")
    assert result is not None
    assert result["alert"] == "SHADOW_AI_DETECTED"
    assert result["risk_level"] == "CRITICAL"


def test_scanner_no_match_returns_none() -> None:
    """audit_traffic returns None for benign log entries."""
    scanner = SentinelScanner()
    result = scanner.audit_traffic("GET https://example.com/api/data HTTP/1.1")
    assert result is None


def test_scanner_bulk_multiple_matches() -> None:
    """audit_bulk returns one finding per matching entry."""
    scanner = SentinelScanner()
    entries = [
        "GET https://api.openai.com/v1/chat/completions",
        "GET https://example.com/safe",
        "POST https://api.anthropic.com/v1/messages",
    ]
    findings = scanner.audit_bulk(entries)
    assert len(findings) == 2
    assert all(f["alert"] == "SHADOW_AI_DETECTED" for f in findings)


def test_scanner_bulk_no_matches() -> None:
    """audit_bulk returns empty list when no unauthorized patterns found."""
    scanner = SentinelScanner()
    findings = scanner.audit_bulk(["GET https://safe.internal/health"])
    assert findings == []


def test_scanner_all_unauthorized_patterns() -> None:
    """Every registered unauthorized pattern produces a finding."""
    scanner = SentinelScanner()
    for pattern in SentinelScanner.UNAUTHORIZED_PATTERNS:
        raw = pattern.replace(r"\.", ".")
        result = scanner.audit_traffic(f"GET https://{raw}/v1/endpoint")
        assert result is not None, f"Pattern not detected: {pattern}"


# ---------------------------------------------------------------------------
# RiskAnalyzer
# ---------------------------------------------------------------------------


def test_risk_analyzer_critical_score() -> None:
    """A single SHADOW_AI_DETECTED finding scores CRITICAL (weight=90)."""
    analyzer = RiskAnalyzer()
    findings = [{"alert": "SHADOW_AI_DETECTED", "endpoint": "api.openai.com"}]
    report = analyzer.analyze(findings)
    assert report.total_score == 90
    assert report.risk_level == "CRITICAL"


def test_risk_analyzer_low_score() -> None:
    """Findings with small weights produce LOW risk level."""
    analyzer = RiskAnalyzer()
    findings = [{"alert": "UNINDEXED_ASSET"}]
    report = analyzer.analyze(findings)
    assert report.total_score == 20
    assert report.risk_level == "MEDIUM"


def test_risk_analyzer_empty_findings() -> None:
    """Empty findings list produces LOW risk and zero score."""
    analyzer = RiskAnalyzer()
    report = analyzer.analyze([])
    assert report.total_score == 0
    assert report.risk_level == "LOW"
    assert report.findings == []


def test_risk_analyzer_annotates_weight() -> None:
    """Each finding in the report has a 'weight' key added."""
    analyzer = RiskAnalyzer()
    findings = [{"alert": "SHADOW_AI_DETECTED"}]
    report = analyzer.analyze(findings)
    assert "weight" in report.findings[0]
    assert report.findings[0]["weight"] == 90


def test_risk_analyzer_unknown_alert_uses_default_weight() -> None:
    """Unknown alert type uses default weight of 10."""
    analyzer = RiskAnalyzer()
    report = analyzer.analyze([{"alert": "SOMETHING_NEW"}])
    assert report.findings[0]["weight"] == 10


# ---------------------------------------------------------------------------
# ThalosOrchestrator pipeline
# ---------------------------------------------------------------------------


def test_orchestrator_invalid_seed_raises() -> None:
    """ThalosOrchestrator rejects invalid seeds at construction."""
    from system.orchestrator import ThalosOrchestrator

    with pytest.raises(ValueError):
        ThalosOrchestrator(seed=0)


def test_orchestrator_pipeline_empty_logs(tmp_path: Path) -> None:
    """Pipeline runs with empty log list, producing LOW risk and a state_hash."""
    from system.orchestrator import ThalosOrchestrator

    statelog = tmp_path / "events.jsonl"
    orch = ThalosOrchestrator(seed=12345678901234567, statelog_path=str(statelog))
    result = orch.run_discovery_pipeline([])

    assert result["risk_level"] == "LOW"
    assert result["risk_score"] == 0
    assert len(result["state_hash"]) == 64
    assert result["findings"] == []


def test_orchestrator_pipeline_with_shadow_ai_log(tmp_path: Path) -> None:
    """Pipeline detects and scores shadow AI findings correctly."""
    from system.orchestrator import ThalosOrchestrator

    statelog = tmp_path / "events.jsonl"
    orch = ThalosOrchestrator(seed=12345678901234567, statelog_path=str(statelog))
    result = orch.run_discovery_pipeline(
        ["GET https://api.openai.com/v1/chat/completions HTTP/1.1"]
    )

    assert result["risk_level"] == "CRITICAL"
    assert result["risk_score"] == 90
    assert len(result["findings"]) == 1


def test_orchestrator_pipeline_writes_statelog(tmp_path: Path) -> None:
    """Pipeline writes a valid STATELOG event to disk."""
    from system.orchestrator import ThalosOrchestrator

    statelog = tmp_path / "events.jsonl"
    orch = ThalosOrchestrator(seed=12345678901234567, statelog_path=str(statelog))
    orch.run_discovery_pipeline([])

    events = [json.loads(line) for line in statelog.read_text().splitlines() if line]
    assert len(events) == 1
    event = events[0]
    assert event["pipeline"] == "discovery"
    assert event["seed"] == 12345678901234567
    assert "state_hash" in event
    assert "risk_level" in event


def test_orchestrator_state_hash_matches_returned_findings(tmp_path: Path) -> None:
    """The returned state_hash is derived from report.findings (the weighted data)."""
    from core.utilities import compute_sha256
    from system.orchestrator import ThalosOrchestrator

    seed = 12345678901234567
    statelog = tmp_path / "events.jsonl"
    orch = ThalosOrchestrator(seed=seed, statelog_path=str(statelog))
    result = orch.run_discovery_pipeline(
        ["GET https://api.openai.com/v1/chat/completions HTTP/1.1"]
    )

    expected_hash = compute_sha256({"seed": seed, "findings": result["findings"]})
    assert result["state_hash"] == expected_hash
