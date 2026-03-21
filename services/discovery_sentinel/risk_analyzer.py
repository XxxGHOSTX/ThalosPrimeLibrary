"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

from dataclasses import dataclass, field


RISK_WEIGHTS = {
    "SHADOW_AI_DETECTED": 90,
    "UNAUTHORIZED_EGRESS": 70,
    "UNSANCTIONED_FRAMEWORK": 60,
    "MISSING_DETERMINISTIC_HEADER": 30,
    "UNINDEXED_ASSET": 20,
}


@dataclass
class RiskReport:
    """Weighted risk report produced by RiskAnalyzer."""

    total_score: int = 0
    findings: list[dict] = field(default_factory=list)
    risk_level: str = "LOW"

    def _compute_level(self) -> None:
        """Update risk_level based on total_score."""
        if self.total_score >= 80:
            self.risk_level = "CRITICAL"
        elif self.total_score >= 50:
            self.risk_level = "HIGH"
        elif self.total_score >= 20:
            self.risk_level = "MEDIUM"
        else:
            self.risk_level = "LOW"


class RiskAnalyzer:
    """Weighted risk scoring engine for discovered shadow AI events."""

    def analyze(self, findings: list[dict]) -> RiskReport:
        """Produce a weighted risk report from a list of findings.

        Args:
            findings: List of finding dicts from SentinelScanner.

        Returns:
            A RiskReport with total score, level, and annotated findings.
        """
        report = RiskReport()
        for finding in findings:
            alert_type = finding.get("alert", "UNKNOWN")
            weight = RISK_WEIGHTS.get(alert_type, 10)
            report.total_score += weight
            report.findings.append({**finding, "weight": weight})
        report._compute_level()
        return report
