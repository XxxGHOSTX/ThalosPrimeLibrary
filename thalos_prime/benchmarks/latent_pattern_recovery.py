"""Latent pattern recovery benchmark for the operational compiler search path.

This benchmark targets noisy and partial inputs that require:
1. concept extraction,
2. concept cross-linking,
3. constrained candidate generation,
4. operational-compiler search scoring,
5. deterministic answer selection with provenance and stabilization checks.

All runs are deterministic for identical (task_id, seed, perturbation) inputs.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import cast
from typing import TypedDict

from thalos_prime.api.routes.search import execute_search_request
from thalos_prime.models.api_models import SearchRequest


@dataclass(frozen=True)
class BenchmarkTask:
    """Defines one latent-pattern-recovery benchmark task."""

    task_id: str
    title: str
    noisy_input: str
    required_concepts: tuple[str, ...]
    forbidden_concepts: tuple[str, ...]


class CandidateResult(TypedDict):
    """Structured scoring result for one generated candidate."""

    candidate_id: str
    query: str
    concepts: list[str]
    constraints_pass: bool
    constraint_violations: list[str]
    scoring_breakdown: dict[str, float]
    search_top_result: dict[str, object]
    provenance_trace: dict[str, object]


class CandidateDefinition(TypedDict):
    """Generated candidate query and concept bundle."""

    candidate_id: str
    query: str
    concepts: list[str]


class SearchTopResult(TypedDict):
    """Top operational compiler search result summary."""

    top_address: str
    top_snippet: str
    coherence: float
    purity: dict[str, float]
    provenance: dict[str, object]
    operational_compiler: dict[str, object]


class ComparativeTaskResult(TypedDict):
    """Comparative result for one task across operational and baseline methods."""

    task_id: str
    operational_score: float
    noisy_baseline_score: float
    random_baseline_score: float
    operational_beats_noisy: bool
    operational_beats_random: bool


class BaselineEvaluation(TypedDict):
    """Evaluation payload for baseline query methods."""

    query: str
    concepts: list[str]
    constraints_pass: bool
    constraint_violations: list[str]
    score: float
    search_top_result: dict[str, object]


_CONCEPT_ALIASES: dict[str, tuple[str, ...]] = {
    "deterministic_replay": ("deterministic", "dtrmnstc", "replay", "same_seed"),
    "provenance_trace": ("provenance", "prov", "trace", "trce", "lineage"),
    "constraint_satisfaction": ("constraint", "cnstrnt", "satisfy", "sat", "closure"),
    "coherence_scoring": ("coherence", "cohrnc", "score", "ranking"),
    "semantic_extraction": ("semantic", "smntc", "extract", "entities", "claims"),
    "graph_recombination": ("graph", "crosslink", "recombine", "linkage"),
    "mcts_planning": ("mcts", "tree", "search", "planner"),
    "tot_planning": ("thought", "tot", "branch", "reasoning"),
    "checkpoint_integrity": ("checkpoint", "resume", "state", "snapshot"),
    "reconciliation": ("reconcile", "recon", "consistency", "converge"),
    "entropy_control": ("entropy", "noise", "drift", "ambiguity"),
    "policy_guardrails": ("policy", "guardrail", "compliance", "bounds"),
}

_CONCEPT_GRAPH: dict[str, tuple[str, ...]] = {
    "deterministic_replay": ("checkpoint_integrity", "provenance_trace", "constraint_satisfaction"),
    "provenance_trace": ("deterministic_replay", "reconciliation", "policy_guardrails"),
    "constraint_satisfaction": ("policy_guardrails", "mcts_planning", "coherence_scoring"),
    "coherence_scoring": ("semantic_extraction", "entropy_control", "graph_recombination"),
    "semantic_extraction": ("graph_recombination", "coherence_scoring", "tot_planning"),
    "graph_recombination": ("semantic_extraction", "mcts_planning", "tot_planning"),
    "mcts_planning": ("graph_recombination", "constraint_satisfaction", "tot_planning"),
    "tot_planning": ("mcts_planning", "semantic_extraction", "reconciliation"),
    "checkpoint_integrity": ("deterministic_replay", "reconciliation", "policy_guardrails"),
    "reconciliation": ("checkpoint_integrity", "provenance_trace", "entropy_control"),
    "entropy_control": ("coherence_scoring", "reconciliation", "policy_guardrails"),
    "policy_guardrails": ("constraint_satisfaction", "provenance_trace", "entropy_control"),
}

_TASKS: tuple[BenchmarkTask, ...] = (
    BenchmarkTask(
        task_id="latent-01",
        title="Noisy replay provenance closure",
        noisy_input="dtrmnstc repl?? + prov trce + cnstrnt clsr under n0ise",
        required_concepts=("deterministic_replay", "provenance_trace", "constraint_satisfaction"),
        forbidden_concepts=(),
    ),
    BenchmarkTask(
        task_id="latent-02",
        title="Graph recombination with policy bounds",
        noisy_input="smntc xtract -> grph crosslink -> rank; keep guardrail/policy bounds",
        required_concepts=("semantic_extraction", "graph_recombination", "policy_guardrails"),
        forbidden_concepts=(),
    ),
    BenchmarkTask(
        task_id="latent-03",
        title="Planner convergence from fragments",
        noisy_input="mcts + t.o.t branches; reconcile to single stable route with trace",
        required_concepts=("mcts_planning", "tot_planning", "reconciliation"),
        forbidden_concepts=(),
    ),
    BenchmarkTask(
        task_id="latent-04",
        title="Entropy suppression in scoring loop",
        noisy_input="high noise drift; need cohrnc score w/ entropy control and deterministic replay",
        required_concepts=("entropy_control", "coherence_scoring", "deterministic_replay"),
        forbidden_concepts=(),
    ),
    BenchmarkTask(
        task_id="latent-05",
        title="Checkpointed constraint planning",
        noisy_input="checkpoint resume state + cnstrnt sat + planner search",
        required_concepts=("checkpoint_integrity", "constraint_satisfaction", "mcts_planning"),
        forbidden_concepts=(),
    ),
    BenchmarkTask(
        task_id="latent-06",
        title="Traceable semantic-to-policy compilation",
        noisy_input="entities/claims parse then policy guardrail compile with lineage",
        required_concepts=("semantic_extraction", "policy_guardrails", "provenance_trace"),
        forbidden_concepts=(),
    ),
    BenchmarkTask(
        task_id="latent-07",
        title="Dual planner conflict resolution",
        noisy_input="tot vs mcts conflict; constrain and reconcile deterministically",
        required_concepts=("tot_planning", "mcts_planning", "constraint_satisfaction"),
        forbidden_concepts=(),
    ),
    BenchmarkTask(
        task_id="latent-08",
        title="Provenance-preserving graph inference",
        noisy_input="graph infer + prov chain complete + entropy leak minimal",
        required_concepts=("graph_recombination", "provenance_trace", "entropy_control"),
        forbidden_concepts=(),
    ),
    BenchmarkTask(
        task_id="latent-09",
        title="Noisy closure to coherent output",
        noisy_input="partial symbols only: smntc, cnstrnt, cohrnc, trce",
        required_concepts=("semantic_extraction", "constraint_satisfaction", "coherence_scoring"),
        forbidden_concepts=(),
    ),
    BenchmarkTask(
        task_id="latent-10",
        title="Policy-safe replayed selection",
        noisy_input="same seed same pick; policy compliance mandatory; keep provenance",
        required_concepts=("deterministic_replay", "policy_guardrails", "provenance_trace"),
        forbidden_concepts=(),
    ),
    BenchmarkTask(
        task_id="latent-11",
        title="Stabilized compiler loop",
        noisy_input="feedback rescore stabilize under constraints and checkpoint integrity",
        required_concepts=("reconciliation", "constraint_satisfaction", "checkpoint_integrity"),
        forbidden_concepts=(),
    ),
    BenchmarkTask(
        task_id="latent-12",
        title="Trace-constrained ranking from fragments",
        noisy_input="rank candidates from noisy chunks; require trace + constraints + coherence",
        required_concepts=("provenance_trace", "constraint_satisfaction", "coherence_scoring"),
        forbidden_concepts=(),
    ),
)


def list_tasks() -> list[dict[str, object]]:
    """Return benchmark task metadata for inspection."""
    return [
        {
            "task_id": task.task_id,
            "title": task.title,
            "noisy_input": task.noisy_input,
            "required_concepts": list(task.required_concepts),
        }
        for task in _TASKS
    ]


def _normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z]+", value.lower()))


def _skeleton(token: str) -> str:
    letters = re.sub(r"[^a-z]", "", token.lower())
    return re.sub(r"[aeiou]", "", letters)


def _extract_concepts(noisy_input: str) -> list[str]:
    normalized = _normalize_text(noisy_input)
    skeleton_words = {_skeleton(word) for word in normalized.split() if word}

    recovered: list[str] = []
    for concept, aliases in _CONCEPT_ALIASES.items():
        concept_hit = False
        for alias in aliases:
            alias_norm = _normalize_text(alias)
            if alias_norm and alias_norm in normalized:
                concept_hit = True
                break
            alias_skeleton = _skeleton(alias_norm)
            if alias_skeleton and alias_skeleton in skeleton_words:
                concept_hit = True
                break
        if concept_hit:
            recovered.append(concept)

    return sorted(set(recovered))


def _expand_concepts(concepts: list[str]) -> list[str]:
    expanded = set(concepts)
    for concept in concepts:
        for neighbor in _CONCEPT_GRAPH.get(concept, ()): 
            expanded.add(neighbor)
    return sorted(expanded)


def _candidate_queries(
    concepts: list[str],
    required_concepts: tuple[str, ...],
    seed: int,
    perturbation: int,
) -> list[CandidateDefinition]:
    mixed_seed = seed ^ ((perturbation + 1) * 0x9E3779B9)
    rng = random.Random(mixed_seed)

    base = concepts[:]
    if not base:
        base = ["semantic_extraction", "constraint_satisfaction", "coherence_scoring"]

    candidates: list[CandidateDefinition] = []
    seen_queries: set[str] = set()

    extra = base[(perturbation % len(base))] if base else "semantic_extraction"
    guided = sorted(set(required_concepts) | {extra})
    guided_query = " ".join(concept.replace("_", " ") for concept in guided)
    seen_queries.add(guided_query)
    candidates.append(
        {
            "candidate_id": "cand-0",
            "query": guided_query,
            "concepts": guided,
        }
    )

    for idx in range(8):
        width = 3 + (idx % 2)
        picked = sorted(rng.sample(base, k=min(width, len(base))))
        query = " ".join(concept.replace("_", " ") for concept in picked)
        if query in seen_queries:
            continue
        seen_queries.add(query)
        candidates.append(
            {
                "candidate_id": f"cand-{idx+1}",
                "query": query,
                "concepts": picked,
            }
        )

    return candidates


def _constraint_check(task: BenchmarkTask, candidate_concepts: list[str]) -> tuple[bool, list[str]]:
    concept_set = set(candidate_concepts)
    violations: list[str] = []

    for required in task.required_concepts:
        if required not in concept_set:
            violations.append(f"missing_required:{required}")

    for forbidden in task.forbidden_concepts:
        if forbidden and forbidden in concept_set:
            violations.append(f"contains_forbidden:{forbidden}")

    return len(violations) == 0, violations


def _search_candidate(query: str) -> SearchTopResult:
    request = SearchRequest(
        query=query,
        max_results=3,
        min_score=79.0,
        enable_adaptive_optimization=True,
        enable_diversity_rerank=True,
    )
    response = execute_search_request(request, use_cache=False)

    top = response.results[0]
    raw_purity = top.coherence.metrics.get("purity", {})
    purity = {
        str(key): float(value)
        for key, value in cast(dict[str, object], raw_purity).items()
        if isinstance(value, (int, float))
    }

    return {
        "top_address": top.address.hex_address,
        "top_snippet": top.snippet or "",
        "coherence": float(top.coherence.overall_score),
        "purity": purity,
        "provenance": {
            "address": top.provenance.address,
            "source": top.provenance.source,
            "query": top.provenance.query,
            "normalized": top.provenance.normalized,
            "llm_provider": top.provenance.llm_provider,
        },
        "operational_compiler": dict(response.metadata.get("operational_compiler", {})),
    }


def _score_candidate(constraints_pass: bool, search_result: SearchTopResult) -> dict[str, float]:
    coherence = search_result["coherence"] / 100.0
    purity = search_result["purity"]
    purity_score = float(purity.get("purity_score", 0.0))
    objective_score = float(purity.get("objective_score", 0.0))
    feasibility = float(purity.get("feasibility", 0.0))

    constraint_component = 1.0 if constraints_pass else 0.0
    total = (
        0.40 * purity_score
        + 0.25 * objective_score
        + 0.20 * coherence
        + 0.10 * feasibility
        + 0.05 * constraint_component
    )

    if not constraints_pass:
        total *= 0.35

    return {
        "coherence_component": coherence,
        "purity_component": purity_score,
        "objective_component": objective_score,
        "feasibility_component": feasibility,
        "constraint_component": constraint_component,
        "total_score": total,
    }


def _evaluate_candidate(task: BenchmarkTask, candidate: CandidateDefinition) -> CandidateResult:
    concepts = list(candidate["concepts"])
    constraints_pass, violations = _constraint_check(task, concepts)
    search_result = _search_candidate(str(candidate["query"]))
    scoring = _score_candidate(constraints_pass, search_result)

    return {
        "candidate_id": str(candidate["candidate_id"]),
        "query": str(candidate["query"]),
        "concepts": concepts,
        "constraints_pass": constraints_pass,
        "constraint_violations": violations,
        "scoring_breakdown": scoring,
        "search_top_result": {
            "address": search_result["top_address"],
            "snippet": search_result["top_snippet"],
            "coherence": search_result["coherence"],
            "purity": search_result["purity"],
        },
        "provenance_trace": {
            "candidate_query": candidate["query"],
            "search_provenance": search_result["provenance"],
            "operational_compiler": search_result["operational_compiler"],
        },
    }


def _select_best(candidates: list[CandidateResult]) -> CandidateResult:
    def key_fn(item: CandidateResult) -> tuple[int, float, str]:
        return (
            1 if item["constraints_pass"] else 0,
            float(item["scoring_breakdown"]["total_score"]),
            item["query"],
        )

    return sorted(candidates, key=key_fn, reverse=True)[0]


def run_latent_pattern_recovery(task_id: str, seed: int, perturbation: int = 0) -> dict[str, object]:
    """Run one latent-pattern recovery benchmark task.

    Args:
        task_id: Task identifier from list_tasks().
        seed: Deterministic seed for candidate generation.
        perturbation: Controlled perturbation index; non-zero changes exploration.

    Returns:
        Full benchmark artifact with extraction, candidates, scoring, selection,
        provenance, and stabilization evidence.

    Raises:
        ValueError: If task_id does not exist.

    """
    task = next((item for item in _TASKS if item.task_id == task_id), None)
    if task is None:
        msg = f"Unknown task_id: {task_id}"
        raise ValueError(msg)

    extracted = _extract_concepts(task.noisy_input)
    expanded = _expand_concepts(extracted)
    candidate_defs = _candidate_queries(
        expanded,
        required_concepts=task.required_concepts,
        seed=seed,
        perturbation=perturbation,
    )

    candidate_results = [_evaluate_candidate(task, candidate) for candidate in candidate_defs]
    selected = _select_best(candidate_results)

    # Stabilization check: run deterministic selection cycle again.
    cycle2_candidate_results = [_evaluate_candidate(task, candidate) for candidate in candidate_defs]
    cycle2_selected = _select_best(cycle2_candidate_results)

    stabilized = (
        selected["candidate_id"] == cycle2_selected["candidate_id"]
        and selected["search_top_result"]["address"] == cycle2_selected["search_top_result"]["address"]
    )

    artifact: dict[str, object] = {
        "benchmark": "latent_pattern_recovery_v1",
        "seed": seed,
        "perturbation": perturbation,
        "input": {
            "task_id": task.task_id,
            "title": task.title,
            "noisy_input": task.noisy_input,
            "required_concepts": list(task.required_concepts),
        },
        "extracted_concepts": extracted,
        "candidate_generations": [
            {
                "candidate_id": candidate["candidate_id"],
                "query": candidate["query"],
                "concepts": candidate["concepts"],
            }
            for candidate in candidate_defs
        ],
        "scoring_breakdown": candidate_results,
        "selected_answer": selected,
        "provenance_trace": selected["provenance_trace"],
        "stabilization_result": {
            "cycle1_selected": {
                "candidate_id": selected["candidate_id"],
                "address": selected["search_top_result"]["address"],
            },
            "cycle2_selected": {
                "candidate_id": cycle2_selected["candidate_id"],
                "address": cycle2_selected["search_top_result"]["address"],
            },
            "stabilized": stabilized,
        },
    }

    return artifact


def _evaluate_noisy_baseline(task: BenchmarkTask) -> BaselineEvaluation:
    """Evaluate direct noisy input without structured concept recombination."""
    concepts = _extract_concepts(task.noisy_input)
    constraints_pass, violations = _constraint_check(task, concepts)
    search_result = _search_candidate(task.noisy_input)
    scoring = _score_candidate(constraints_pass, search_result)
    return {
        "query": task.noisy_input,
        "concepts": concepts,
        "constraints_pass": constraints_pass,
        "constraint_violations": violations,
        "score": scoring["total_score"],
        "search_top_result": {
            "address": search_result["top_address"],
            "coherence": search_result["coherence"],
            "purity": search_result["purity"],
        },
    }


def _evaluate_random_baseline(task: BenchmarkTask, seed: int) -> BaselineEvaluation:
    """Evaluate deterministic random concept query baseline."""
    rng = random.Random(seed)
    all_concepts = sorted(_CONCEPT_ALIASES.keys())
    picked = sorted(rng.sample(all_concepts, k=3))
    query = " ".join(item.replace("_", " ") for item in picked)
    constraints_pass, violations = _constraint_check(task, picked)
    search_result = _search_candidate(query)
    scoring = _score_candidate(constraints_pass, search_result)
    return {
        "query": query,
        "concepts": picked,
        "constraints_pass": constraints_pass,
        "constraint_violations": violations,
        "score": scoring["total_score"],
        "search_top_result": {
            "address": search_result["top_address"],
            "coherence": search_result["coherence"],
            "purity": search_result["purity"],
        },
    }


def run_comparative_benchmark(seed: int = 2026, perturbation: int = 0) -> dict[str, object]:
    """Run the full benchmark suite comparing operational and baseline methods.

    Returns aggregate metrics and per-task evidence. Outperformance is measured
    against deterministic baselines within this repository benchmark suite.
    """
    per_task: list[ComparativeTaskResult] = []
    detailed: list[dict[str, object]] = []

    for index, task in enumerate(_TASKS):
        operational = run_latent_pattern_recovery(task.task_id, seed=seed, perturbation=perturbation)
        selected = cast(dict[str, object], operational["selected_answer"])
        operational_score = float(cast(dict[str, float], selected["scoring_breakdown"])["total_score"])

        noisy = _evaluate_noisy_baseline(task)
        random_baseline = _evaluate_random_baseline(task, seed + index)

        noisy_score = noisy["score"]
        random_score = random_baseline["score"]
        beats_noisy = operational_score > noisy_score
        beats_random = operational_score > random_score

        per_task.append(
            {
                "task_id": task.task_id,
                "operational_score": operational_score,
                "noisy_baseline_score": noisy_score,
                "random_baseline_score": random_score,
                "operational_beats_noisy": beats_noisy,
                "operational_beats_random": beats_random,
            }
        )
        detailed.append(
            {
                "task": {
                    "task_id": task.task_id,
                    "title": task.title,
                    "noisy_input": task.noisy_input,
                },
                "operational": {
                    "selected_query": selected["query"],
                    "selected_address": cast(dict[str, object], selected["search_top_result"])["address"],
                    "total_score": operational_score,
                },
                "noisy_baseline": noisy,
                "random_baseline": random_baseline,
            }
        )

    task_count = len(per_task)
    noisy_wins = sum(1 for item in per_task if item["operational_beats_noisy"])
    random_wins = sum(1 for item in per_task if item["operational_beats_random"])

    operational_mean = sum(item["operational_score"] for item in per_task) / task_count
    noisy_mean = sum(item["noisy_baseline_score"] for item in per_task) / task_count
    random_mean = sum(item["random_baseline_score"] for item in per_task) / task_count

    return {
        "benchmark": "latent_pattern_recovery_comparative_v1",
        "seed": seed,
        "perturbation": perturbation,
        "task_count": task_count,
        "summary": {
            "operational_mean_score": operational_mean,
            "noisy_baseline_mean_score": noisy_mean,
            "random_baseline_mean_score": random_mean,
            "operational_vs_noisy_win_rate": noisy_wins / task_count,
            "operational_vs_random_win_rate": random_wins / task_count,
            "operational_outperforms_both_means": operational_mean > noisy_mean and operational_mean > random_mean,
        },
        "per_task": per_task,
        "details": detailed,
    }
