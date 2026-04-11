#!/usr/bin/env python3
"""Deterministic benchmark harness for search ranking quality.

Compares baseline (no expansion, no diversity rerank) versus enhanced search
behavior on a fixed query suite using NDCG@k and diversity metrics.
"""

from __future__ import annotations

import argparse
import asyncio
import math
from dataclasses import dataclass

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
class BenchmarkResult:
    query: str
    ndcg_enhanced: float
    ndcg_baseline: float
    diversity_enhanced: float
    diversity_baseline: float


def _dcg(labels: list[float]) -> float:
    total = 0.0
    for idx, label in enumerate(labels, start=1):
        total += (2**label - 1) / math.log2(idx + 1)
    return total


def _ndcg_at_k(labels: list[float], k: int) -> float:
    observed = labels[:k]
    ideal = sorted(labels, reverse=True)[:k]
    denom = _dcg(ideal)
    if denom == 0:
        return 0.0
    return _dcg(observed) / denom


def _jaccard(text_a: str, text_b: str) -> float:
    set_a = set(text_a.lower().split())
    set_b = set(text_b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _diversity_score(snippets: list[str]) -> float:
    if len(snippets) < 2:
        return 1.0
    similarities: list[float] = []
    for left in range(len(snippets)):
        for right in range(left + 1, len(snippets)):
            similarities.append(_jaccard(snippets[left], snippets[right]))
    if not similarities:
        return 1.0
    return 1.0 - (sum(similarities) / len(similarities))


async def _run_single(query: str, max_results: int, mode: SearchMode) -> BenchmarkResult:
    remote_policy = RemoteAccessPolicy.LOCAL_ONLY
    remote_consent = False

    baseline = await search(
        SearchRequest(
            query=query,
            max_results=max_results,
            mode=mode,
            remote_access_policy=remote_policy,
            remote_consent=remote_consent,
            enable_query_expansion=False,
            enable_diversity_rerank=False,
        ),
    )

    enhanced = await search(
        SearchRequest(
            query=query,
            max_results=max_results,
            mode=mode,
            remote_access_policy=remote_policy,
            remote_consent=remote_consent,
            enable_query_expansion=True,
            enable_diversity_rerank=True,
        ),
    )

    baseline_labels = [
        (float(item.coherence.overall_score) / 100.0)
        + (float(item.coherence.metrics.get("combined_score", 0.0)) / 100.0)
        for item in baseline.results
    ]
    enhanced_labels = [
        (float(item.coherence.overall_score) / 100.0)
        + (float(item.coherence.metrics.get("combined_score", 0.0)) / 100.0)
        for item in enhanced.results
    ]

    baseline_diversity = _diversity_score([item.snippet or "" for item in baseline.results])
    enhanced_diversity = _diversity_score([item.snippet or "" for item in enhanced.results])

    return BenchmarkResult(
        query=query,
        ndcg_enhanced=_ndcg_at_k(enhanced_labels, max_results),
        ndcg_baseline=_ndcg_at_k(baseline_labels, max_results),
        diversity_enhanced=enhanced_diversity,
        diversity_baseline=baseline_diversity,
    )


async def _run_benchmark(max_results: int, mode: SearchMode) -> list[BenchmarkResult]:
    return [await _run_single(query, max_results=max_results, mode=mode) for query in QUERY_SUITE]


def _print_report(results: list[BenchmarkResult]) -> None:
    print("query\tndcg_baseline\tndcg_enhanced\tdiversity_baseline\tdiversity_enhanced")
    for row in results:
        print(
            f"{row.query}\t{row.ndcg_baseline:.4f}\t{row.ndcg_enhanced:.4f}\t"
            f"{row.diversity_baseline:.4f}\t{row.diversity_enhanced:.4f}",
        )

    avg_ndcg_base = sum(r.ndcg_baseline for r in results) / len(results)
    avg_ndcg_enh = sum(r.ndcg_enhanced for r in results) / len(results)
    avg_div_base = sum(r.diversity_baseline for r in results) / len(results)
    avg_div_enh = sum(r.diversity_enhanced for r in results) / len(results)

    print("\nsummary")
    print(f"avg_ndcg_baseline={avg_ndcg_base:.4f}")
    print(f"avg_ndcg_enhanced={avg_ndcg_enh:.4f}")
    print(f"avg_diversity_baseline={avg_div_base:.4f}")
    print(f"avg_diversity_enhanced={avg_div_enh:.4f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Thalos Prime search ranking quality")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--mode", choices=["local", "hybrid"], default="local")
    args = parser.parse_args()

    mode = SearchMode.LOCAL if args.mode == "local" else SearchMode.HYBRID
    results = asyncio.run(_run_benchmark(max_results=args.max_results, mode=mode))
    _print_report(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
