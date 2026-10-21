"""API tests for adaptive finite-domain representation solving."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from thalos_prime.api.routes.discovery import router


def _client() -> TestClient:
    """Create an isolated application around the discovery router."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_solve_endpoint_finds_conflict_and_review_candidates() -> None:
    response = _client().post("/solve", json={
        "problem_id": "throughput-conflict",
        "variables": [{"name": "throughput", "domain": list(range(13))}],
        "constraints": [
            {"name": "minimum", "left_variable": "throughput", "operator": "ge", "right_value": 10},
            {"name": "maximum", "left_variable": "throughput", "operator": "le", "right_value": 5},
        ],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["verification_status"] == "finite_domain_unsatisfiable"
    assert body["verified"] is True
    assert set(body["conflict_core"]) == {"minimum", "maximum"}
    assert {item["constraint"] for item in body["repair_candidates"]} == {"minimum", "maximum"}


def test_solve_endpoint_selects_mrv_on_large_restricted_problem() -> None:
    variables = [{"name": f"A{index}", "domain": [0, 1]} for index in range(8)]
    variables.append({"name": "Z", "domain": list(range(20))})
    response = _client().post("/solve", json={
        "problem_id": "large-late-contradiction",
        "variables": variables,
        "constraints": [
            {"name": "z-only-999", "left_variable": "Z", "operator": "eq", "right_value": 999}
        ],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["selected_strategy"] == "mrv"
    runs = {run["strategy"]: run for run in body["comparison_runs"]}
    assert runs["mrv"]["nodes_expanded"] < runs["fixed_order"]["nodes_expanded"]
    assert body["verified"] is True


def test_solve_endpoint_rejects_ambiguous_relations() -> None:
    response = _client().post("/solve", json={
        "problem_id": "bad-problem",
        "variables": [{"name": "x", "domain": [1, 2]}],
        "constraints": [
            {"name": "bad", "left_variable": "x", "operator": "eq", "right_value": 1,
             "right_variable": "x"}
        ],
    })
    assert response.status_code == 422
