"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

import sys
import argparse

from fastapi import FastAPI
from pydantic import BaseModel

from .scanner import SentinelScanner
from .risk_analyzer import RiskAnalyzer
from .agentic_audit import AgenticAuditor
from core.utilities import append_jsonl, now_iso, compute_sha256, validate_seed

app = FastAPI(
    title="Thalos Sentinel MCP Server",
    version="2.0.0",
    description="© 2026 Tony Ray Macier III. Model Context Protocol server for shadow AI discovery.",
)

_scanner = SentinelScanner()
_analyzer = RiskAnalyzer()
_auditor = AgenticAuditor()

# MCP tool definitions — consumed by the Concierge Extension via McpClient
TOOLS = [
    {
        "name": "sentinel/run-scan",
        "description": "Scan log entries for unauthorized AI API egress patterns. Returns all findings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "log_entries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Network log lines to scan",
                },
                "seed": {
                    "type": "integer",
                    "description": "64-bit execution seed for deterministic reproducibility",
                },
            },
            "required": ["log_entries", "seed"],
        },
    },
    {
        "name": "sentinel/risk-report",
        "description": "Generate a weighted risk report from scan findings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "description": "Findings list from a previous sentinel/run-scan call",
                },
                "seed": {"type": "integer", "description": "64-bit execution seed"},
            },
            "required": ["findings", "seed"],
        },
    },
    {
        "name": "sentinel/agentic-audit",
        "description": "Evaluate a website's Agentic Web readiness (AI-SEO audit).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target URL"},
                "html_content": {"type": "string", "description": "Raw HTML content of the page"},
            },
            "required": ["url", "html_content"],
        },
    },
]


class ToolCallRequest(BaseModel):
    """Request body for an MCP tool call."""

    name: str
    arguments: dict = {}


@app.post("/tools/list")
def list_tools() -> dict:
    """Return all available MCP tools."""
    return {"tools": TOOLS}


@app.post("/tools/call")
def call_tool(request: ToolCallRequest) -> dict:
    """Invoke a named MCP tool with the provided arguments."""
    name = request.name
    args = request.arguments

    if name == "sentinel/run-scan":
        seed = args.get("seed", 0)
        log_entries = args.get("log_entries", [])
        findings = _scanner.audit_bulk(log_entries)
        state_hash = compute_sha256({"seed": seed, "findings": findings})
        event = {
            "tool": "sentinel/run-scan",
            "seed": seed,
            "findings_count": len(findings),
            "state_hash": state_hash,
            "timestamp": now_iso(),
        }
        append_jsonl("STATELOG/discovery.jsonl", event)
        return {
            "content": [{"type": "text", "text": str(findings)}],
            "state_hash": state_hash,
            "isError": False,
        }

    if name == "sentinel/risk-report":
        seed = args.get("seed", 0)
        findings = args.get("findings", [])
        report = _analyzer.analyze(findings)
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Risk Level: {report.risk_level} | Score: {report.total_score} | "
                        f"Findings: {len(report.findings)}"
                    ),
                }
            ],
            "risk_level": report.risk_level,
            "risk_score": report.total_score,
            "isError": False,
        }

    if name == "sentinel/agentic-audit":
        url = args.get("url", "")
        html_content = args.get("html_content", "")
        result = _auditor.audit(url, html_content)
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Agentic Score: {result.agentic_score}/100 | "
                        f"llms.txt: {result.has_llms_txt} | "
                        f"Structured Data: {result.has_structured_data} | "
                        f"Recommendations: {len(result.recommendations)}"
                    ),
                }
            ],
            "agentic_score": result.agentic_score,
            "recommendations": result.recommendations,
            "isError": False,
        }

    return {
        "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
        "isError": True,
    }


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "thalos-sentinel-mcp", "version": "2.0.0"}


def main() -> None:
    """CLI entry point for the Sentinel MCP server."""
    parser = argparse.ArgumentParser(description="Thalos Prime Sentinel MCP Server")
    parser.add_argument("--seed", type=int, required=True, help="64-bit execution seed (required)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    try:
        validate_seed(args.seed)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
