#!/usr/bin/env python3
"""Advanced search audit pipeline with actionable optimization report.

Runs deterministic scenario comparisons against the live in-process search route,
exports JSON and Markdown artifacts, and computes concrete improvement gaps.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from thalos_prime.api.routes.search import search
from thalos_prime.models.api_models import RemoteAccessPolicy, SearchMode, SearchRequest

QUERY_SUITE = [
    "define deterministic coherence",
    "explore relationships between graph reasoning and language",
    "what is symbolic constraint optimization",
    "compare narrative structure and lexical density",
    "how do retrieval and generation interact",
]


@dataclass(frozen=True)
class Scenario:
    """Benchmark scenario configuration."""

    name: str
    mode: SearchMode
    enable_query_expansion: bool
    enable_diversity_rerank: bool
    enable_adaptive_optimization: bool
    diversity_lambda: float


@dataclass(frozen=True)
class QueryMeasurement:
    """Single query measurement for one scenario."""

    query: str
    latency_ms: float
    ndcg: float
    diversity: float
    novelty_index: float
    result_count: int
    remote_pages_federated: int


@dataclass(frozen=True)
class ScenarioReport:
    """Aggregated scenario report."""

    scenario: str
    avg_latency_ms: float
    avg_ndcg: float
    avg_diversity: float
    avg_novelty_index: float
    avg_result_count: float
    total_remote_pages_federated: int
    measurements: list[QueryMeasurement]


def _dcg(labels: list[float]) -> float:
    total = 0.0
    for idx, label in enumerate(labels, start=1):
        total += (2**label - 1) / math.log2(idx + 1)
    return total


def _ndcg_at_k(labels: list[float], k: int) -> float:
    observed = labels[:k]
    ideal = sorted(labels, reverse=True)[:k]
    denom = _dcg(ideal)
    if denom == 0.0:
        return 0.0
    return _dcg(observed) / denom


def _jaccard(text_a: str, text_b: str) -> float:
    set_a = set(text_a.lower().split())
    set_b = set(text_b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _diversity(snippets: list[str]) -> float:
    if len(snippets) < 2:
        return 1.0
    similarities: list[float] = []
    for i in range(len(snippets)):
        for j in range(i + 1, len(snippets)):
            similarities.append(_jaccard(snippets[i], snippets[j]))
    if not similarities:
        return 1.0
    return 1.0 - (sum(similarities) / len(similarities))


async def _run_scenario_query(query: str, max_results: int, scenario: Scenario) -> QueryMeasurement:
    req = SearchRequest(
        query=query,
        max_results=max_results,
        mode=scenario.mode,
        remote_access_policy=RemoteAccessPolicy.LOCAL_ONLY,
        remote_consent=False,
        enable_query_expansion=scenario.enable_query_expansion,
        enable_diversity_rerank=scenario.enable_diversity_rerank,
        enable_adaptive_optimization=scenario.enable_adaptive_optimization,
        diversity_lambda=scenario.diversity_lambda,
    )

    started = perf_counter()
    response = await search(req)
    latency_ms = (perf_counter() - started) * 1000.0

    labels = [
        (float(item.coherence.overall_score) / 100.0)
        + (float(item.coherence.metrics.get("combined_score", 0.0)) / 100.0)
        for item in response.results
    ]
    snippets = [item.snippet or "" for item in response.results]

    novelty_raw = response.metadata.get("novelty_index", 0.0)
    novelty_index = float(novelty_raw) if isinstance(novelty_raw, int | float) else 0.0

    remote_pages_raw = response.metadata.get("remote_pages_federated", 0)
    remote_pages = int(remote_pages_raw) if isinstance(remote_pages_raw, int | float) else 0

    return QueryMeasurement(
        query=query,
        latency_ms=latency_ms,
        ndcg=_ndcg_at_k(labels, max_results),
        diversity=_diversity(snippets),
        novelty_index=novelty_index,
        result_count=len(response.results),
        remote_pages_federated=remote_pages,
    )


async def _run_scenario(max_results: int, scenario: Scenario) -> ScenarioReport:
    measurements: list[QueryMeasurement] = []
    for query in QUERY_SUITE:
        measurements.append(await _run_scenario_query(query, max_results=max_results, scenario=scenario))

    count = float(len(measurements))
    return ScenarioReport(
        scenario=scenario.name,
        avg_latency_ms=sum(m.latency_ms for m in measurements) / count,
        avg_ndcg=sum(m.ndcg for m in measurements) / count,
        avg_diversity=sum(m.diversity for m in measurements) / count,
        avg_novelty_index=sum(m.novelty_index for m in measurements) / count,
        avg_result_count=sum(float(m.result_count) for m in measurements) / count,
        total_remote_pages_federated=sum(m.remote_pages_federated for m in measurements),
        measurements=measurements,
    )


def _find_needs(reports: list[ScenarioReport]) -> list[str]:
    by_name = {report.scenario: report for report in reports}
    needs: list[str] = []

    baseline = by_name.get("baseline_local")
    enhanced = by_name.get("enhanced_local")
    adaptive = by_name.get("adaptive_local")

    if baseline and enhanced:
        ndcg_gain = enhanced.avg_ndcg - baseline.avg_ndcg
        diversity_gain = enhanced.avg_diversity - baseline.avg_diversity
        if ndcg_gain <= 0.003:
            needs.append(
                "Relevance signal remains saturated in local deterministic mode; add harder query sets and stronger lexical-semantic discriminators.",
            )
        if diversity_gain <= 0.01:
            needs.append(
                "Diversity gain is minimal; introduce broader candidate pools or corpus-backed retrieval to improve novelty spread.",
            )

    if adaptive and enhanced:
        novelty_gain = adaptive.avg_novelty_index - enhanced.avg_novelty_index
        if novelty_gain <= 0.01:
            needs.append(
                "Adaptive optimization impact is limited; tune intent profiles with offline calibration over judged datasets.",
            )

    if any(report.total_remote_pages_federated == 0 for report in reports):
        needs.append(
            "Remote federation benchmark is not represented in this run (local-only policy); run a consent-enabled hybrid benchmark in a network-allowed environment.",
        )

    max_latency = max((report.avg_latency_ms for report in reports), default=0.0)
    if max_latency > 500.0:
        needs.append(
            "Average query latency exceeded 500ms in at least one scenario; profile decoding and ensemble generation hot paths.",
        )

    if not needs:
        needs.append("No immediate blocking gaps detected in the audited local scenarios.")

    return needs


def _as_json_serializable(reports: list[ScenarioReport], needs: list[str]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "query_suite": QUERY_SUITE,
        "scenarios": [
            {
                **{k: v for k, v in asdict(report).items() if k != "measurements"},
                "measurements": [asdict(m) for m in report.measurements],
            }
            for report in reports
        ],
        "needs": needs,
    }


def _write_markdown(path: Path, reports: list[ScenarioReport], needs: list[str]) -> None:
    lines: list[str] = []
    lines.append("# Advanced Search Audit Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(tz=UTC).isoformat()}")
    lines.append("")
    lines.append("## Scenario Summary")
    lines.append("")
    lines.append("| Scenario | Avg Latency (ms) | Avg NDCG | Avg Diversity | Avg Novelty | Avg Results | Remote Pages |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for report in reports:
        lines.append(
            "| "
            f"{report.scenario} | {report.avg_latency_ms:.2f} | {report.avg_ndcg:.4f} | "
            f"{report.avg_diversity:.4f} | {report.avg_novelty_index:.4f} | "
            f"{report.avg_result_count:.2f} | {report.total_remote_pages_federated} |"
        )

    lines.append("")
    lines.append("## Still Needed")
    lines.append("")
    for item in needs:
        lines.append(f"- {item}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _run(max_results: int) -> tuple[list[ScenarioReport], list[str]]:
    scenarios = [
        Scenario(
            name="baseline_local",
            mode=SearchMode.LOCAL,
            enable_query_expansion=False,
            enable_diversity_rerank=False,
            enable_adaptive_optimization=False,
            diversity_lambda=0.70,
        ),
        Scenario(
            name="enhanced_local",
            mode=SearchMode.LOCAL,
            enable_query_expansion=True,
            enable_diversity_rerank=True,
            enable_adaptive_optimization=False,
            diversity_lambda=0.70,
        ),
        Scenario(
            name="adaptive_local",
            mode=SearchMode.LOCAL,
            enable_query_expansion=True,
            enable_diversity_rerank=True,
            enable_adaptive_optimization=True,
            diversity_lambda=0.70,
        ),
    ]

    reports: list[ScenarioReport] = []
    for scenario in scenarios:
        reports.append(await _run_scenario(max_results=max_results, scenario=scenario))

    needs = _find_needs(reports)
    return reports, needs


def main() -> int:
    parser = argparse.ArgumentParser(description="Run advanced Thalos Prime search audit")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--json-out", default="data/advanced_search_audit_report.json")
    parser.add_argument("--md-out", default="data/advanced_search_audit_report.md")
    args = parser.parse_args()

    reports, needs = asyncio.run(_run(max_results=args.max_results))
    payload = _as_json_serializable(reports, needs)

    json_path = Path(args.json_out)
    md_path = Path(args.md_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_markdown(md_path, reports, needs)

    print(f"Wrote JSON report: {json_path}")
    print(f"Wrote Markdown report: {md_path}")
    print("Needs:")
    for need in needs:
        print(f"- {need}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
