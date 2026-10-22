"""API tests for experiment planning and candidate comparison."""

from __future__ import annotations

from fastapi.testclient import TestClient

from thalos_prime.api.server import app

client = TestClient(app)


def make_payload() -> dict[str, object]:
    """Build a deterministic compare request with one baseline and one candidate."""
    spec = {
        "experiment_id": "api-exp-1",
        "task_family": "repository-fix",
        "task_description": "Compare recorded regression-suite outcomes",
        "dataset_version": "api-fixture-v1",
        "baseline_candidate_id": "baseline",
        "primary_metric": "pass_rate",
        "metrics": [
            {
                "name": "pass_rate",
                "direction": "maximize",
                "required": True,
                "target_value": 0.8,
            }
        ],
        "require_evidence": True,
        "configuration_digest": "a" * 64,
    }

    def candidate(candidate_id: str, pass_rate: float) -> dict[str, object]:
        return {
            "run_id": f"run-{candidate_id}",
            "candidate_id": candidate_id,
            "approach": "test approach",
            "representation_id": "graph-v1",
            "implementation_version": "commit-abc123",
            "environment_fingerprint": "python312-lockfile-v1",
            "model_versions": {"model": "fixture-1"},
            "configuration_digest": "b" * 64,
            "metric_samples": {"pass_rate": [pass_rate, pass_rate]},
            "tests_passed": True,
            "test_ids": ["regression-1"],
            "evidence_refs": [f"artifact:{candidate_id}"],
            "elapsed_ms": 25.0,
            "cost_usd": 0.1,
            "failure_summary": [],
        }

    return {"spec": spec, "runs": [candidate("baseline", 0.7), candidate("candidate", 0.9)]}


def test_default_plan_endpoint_returns_a_validated_workflow() -> None:
    response = client.get("/api/v1/experiments/plan/default")
    assert response.status_code == 200
    body = response.json()
    assert body["plan_id"] == "thalos-research-v1"
    assert body["stages"][-1]["stage_id"] == "persist_report"


def test_compare_endpoint_returns_ranked_evidence_report() -> None:
    response = client.post("/api/v1/experiments/compare", json=make_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["ranked_candidate_ids"] == ["candidate"]
    assert body["spec"]["dataset_version"] == "api-fixture-v1"
    assert len(body["report_digest"]) == 64


def test_compare_endpoint_rejects_missing_baseline() -> None:
    payload = make_payload()
    payload["runs"] = [payload["runs"][1]]  # type: ignore[index]
    response = client.post("/api/v1/experiments/compare", json=payload)
    assert response.status_code == 400
