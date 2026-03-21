"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

import re


class SentinelScanner:
    """
    Identifies unauthorized LLM API calls by analyzing egress traffic patterns.
    Targets Shadow Agents spun up without IT approval.
    """

    UNAUTHORIZED_PATTERNS = [
        r"api\.openai\.com",
        r"api\.anthropic\.com",
        r"v1/chat/completions",
        r"bedrock-runtime",
        r"vertexai\.googleapis\.com",
        r"api\.cohere\.ai",
        r"generativelanguage\.googleapis\.com",
    ]

    def audit_traffic(self, log_entry: str) -> dict | None:
        """Scan a single log entry for unauthorized AI API calls.

        Args:
            log_entry: A network log line to inspect.

        Returns:
            A finding dict if a pattern matches, else None.
        """
        for pattern in self.UNAUTHORIZED_PATTERNS:
            if re.search(pattern, log_entry):
                return {
                    "alert": "SHADOW_AI_DETECTED",
                    "endpoint": pattern,
                    "risk_level": "CRITICAL",
                    "matched_entry": log_entry[:200],
                }
        return None

    def audit_bulk(self, log_entries: list[str]) -> list[dict]:
        """Scan multiple log entries and return all findings.

        Args:
            log_entries: List of network log lines to inspect.

        Returns:
            List of finding dicts (one per match).
        """
        findings = []
        for entry in log_entries:
            result = self.audit_traffic(entry)
            if result:
                findings.append(result)
        return findings
