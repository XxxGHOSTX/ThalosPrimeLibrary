from __future__ import annotations

from fastapi.testclient import TestClient

from thalos_prime.api.server import app

client = TestClient(app)


def test_search_response_has_individuation_metadata() -> None:
    response = client.post(
        "/api/v1/search",
        json={"query": "global safe clear test api check stable", "max_results": 1},
    )
    assert response.status_code == 200
    payload = response.json()

    metadata = payload.get("metadata", {})
    assert "individuation" in metadata
    assert metadata["individuation"]["policy_version"] == "individuation-v1"
    assert "operational_compiler" in metadata

    compiler = metadata["operational_compiler"]
    assert compiler["objective"] == "argmax U*N*F*E subject to K<=0"
    assert set(compiler["purity_functional"].keys()) == {"alpha", "beta", "gamma", "delta", "lambda"}


def test_search_results_include_purity_metrics() -> None:
    response = client.post(
        "/api/v1/search",
        json={
            "query": "constraint aligned deterministic synthesis",
            "max_results": 2,
            "enable_adaptive_optimization": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()

    results = payload.get("results", [])
    assert results
    for result in results:
        metrics = result["coherence"]["metrics"]
        assert "purity" in metrics
        purity = metrics["purity"]
        assert 0.0 <= purity["utility"] <= 1.0
        assert 0.0 <= purity["novelty"] <= 1.0
        assert 0.0 <= purity["feasibility"] <= 1.0
        assert 0.0 <= purity["explainability"] <= 1.0
        assert 0.0 <= purity["determinism"] <= 1.0
        assert 0.0 <= purity["provenance_integrity"] <= 1.0
        assert 0.0 <= purity["entropy_leak"] <= 1.0
        assert 0.0 <= purity["objective_score"] <= 1.0
        assert 0.0 <= purity["purity_score"] <= 1.0


def test_operational_compiler_feedback_stabilizes() -> None:
    request_body = {
        "query": "self stabilizing epistemic loop",
        "max_results": 3,
        "enable_adaptive_optimization": True,
    }

    response_1 = client.post("/api/v1/search", json=request_body)
    response_2 = client.post("/api/v1/search", json=request_body)
    assert response_1.status_code == 200
    assert response_2.status_code == 200

    metadata_1 = response_1.json()["metadata"]["operational_compiler"]["feedback"]
    metadata_2 = response_2.json()["metadata"]["operational_compiler"]["feedback"]

    assert metadata_1["cycles"] == 2
    assert metadata_2["cycles"] == 2
    assert metadata_1["stabilized"] is True
    assert metadata_2["stabilized"] is True
    assert metadata_1["cycle2_purity_mean"] == metadata_2["cycle2_purity_mean"]


def test_individuation_header_present() -> None:
    response = client.post(
        "/api/v1/search",
        json={"query": "deterministic governance", "max_results": 1},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Thalos-Individuation-Policy") == "individuation-v1"
