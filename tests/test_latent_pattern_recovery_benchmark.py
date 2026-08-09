"""Tests for latent pattern recovery benchmark behavior.

These tests verify deterministic reproducibility, controlled perturbation,
constraint handling, and artifact structure.
"""

from __future__ import annotations

from typing import Any, cast

from thalos_prime.benchmarks.latent_pattern_recovery import (
    list_tasks,
    run_comparative_benchmark,
    run_latent_pattern_recovery,
)


def test_benchmark_task_suite_size() -> None:
    """Benchmark suite must remain non-trivial (10-20 tasks)."""
    tasks = list_tasks()
    assert 10 <= len(tasks) <= 20


def test_benchmark_artifact_structure() -> None:
    """Artifact contains the full operational compiler evidence object."""
    artifact = run_latent_pattern_recovery(task_id="latent-01", seed=1337, perturbation=0)

    assert set(artifact.keys()) >= {
        "input",
        "extracted_concepts",
        "candidate_generations",
        "scoring_breakdown",
        "selected_answer",
        "provenance_trace",
        "stabilization_result",
    }
    assert artifact["benchmark"] == "latent_pattern_recovery_v1"


def test_benchmark_deterministic_same_seed() -> None:
    """Same task and seed yields identical selected answer and stabilization."""
    run1 = run_latent_pattern_recovery(task_id="latent-03", seed=4242, perturbation=0)
    run2 = run_latent_pattern_recovery(task_id="latent-03", seed=4242, perturbation=0)

    assert run1 == run2


def test_benchmark_perturbation_changes_valid_result() -> None:
    """Controlled perturbation should alter exploration while remaining valid."""
    baseline = run_latent_pattern_recovery(task_id="latent-04", seed=4242, perturbation=0)
    perturbed = run_latent_pattern_recovery(task_id="latent-04", seed=4242, perturbation=1)

    base_selected = cast(dict[str, Any], baseline["selected_answer"])
    pert_selected = cast(dict[str, Any], perturbed["selected_answer"])

    assert base_selected["constraints_pass"] is True
    assert pert_selected["constraints_pass"] is True

    changed = (
        base_selected["candidate_id"] != pert_selected["candidate_id"]
        or base_selected["search_top_result"]["address"]
        != pert_selected["search_top_result"]["address"]
    )
    assert changed is True


def test_required_concepts_impact_constraint_filtering() -> None:
    """Selected answer must satisfy task-level required concepts."""
    artifact = run_latent_pattern_recovery(task_id="latent-10", seed=2121, perturbation=0)

    selected = cast(dict[str, Any], artifact["selected_answer"])
    input_payload = cast(dict[str, Any], artifact["input"])
    required = set(cast(list[str], input_payload["required_concepts"]))
    selected_concepts = set(cast(list[str], selected["concepts"]))

    assert selected["constraints_pass"] is True
    assert required.issubset(selected_concepts)


def test_comparative_benchmark_operational_beats_baselines() -> None:
    """Operational compiler should beat deterministic baselines on this suite."""
    report = run_comparative_benchmark(seed=2026, perturbation=0)
    summary = cast(dict[str, Any], report["summary"])

    assert int(cast(int, report["task_count"])) >= 10
    assert summary["operational_outperforms_both_means"] is True
    assert summary["operational_vs_noisy_win_rate"] >= 0.65
    assert summary["operational_vs_random_win_rate"] >= 0.75
