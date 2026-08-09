"""Tests for knowledge_engine.api.router."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from thalos_prime.knowledge_engine.api.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_ingest_text() -> None:
    resp = client.post("/knowledge/ingest", json={"text": "The sky is blue.", "source_type": "text"})
    assert resp.status_code == 200
    data = resp.json()
    assert "source_id" in data
    assert "content_hash" in data


def test_ingest_no_content() -> None:
    resp = client.post("/knowledge/ingest", json={"source_type": "text"})
    assert resp.status_code == 422


def test_extract_text() -> None:
    ingest_resp = client.post("/knowledge/ingest", json={"text": "Extract this text. It has sentences.", "source_type": "text"})
    source_id = ingest_resp.json()["source_id"]
    resp = client.post(f"/knowledge/extract/{source_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "artifact_id" in data
    assert "extracted_text" in data


def test_extract_not_found() -> None:
    resp = client.post("/knowledge/extract/nonexistent-id")
    assert resp.status_code == 404


def test_translate_artifact() -> None:
    ingest_resp = client.post("/knowledge/ingest", json={"text": "This is English text.", "source_type": "text"})
    source_id = ingest_resp.json()["source_id"]
    extract_resp = client.post(f"/knowledge/extract/{source_id}")
    artifact_id = extract_resp.json()["artifact_id"]
    resp = client.post(f"/knowledge/translate/{artifact_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "stability_score" in data


def test_translate_not_found() -> None:
    resp = client.post("/knowledge/translate/nonexistent-id")
    assert resp.status_code == 404


def test_claims_endpoint() -> None:
    ingest_resp = client.post("/knowledge/ingest", json={"text": "The sky is blue. Water flows downward. Trees grow tall.", "source_type": "text"})
    source_id = ingest_resp.json()["source_id"]
    extract_resp = client.post(f"/knowledge/extract/{source_id}")
    artifact_id = extract_resp.json()["artifact_id"]
    resp = client.post(f"/knowledge/claims/{artifact_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "claims" in data
    assert "count" in data


def test_claims_not_found() -> None:
    resp = client.post("/knowledge/claims/nonexistent-id")
    assert resp.status_code == 404


def test_query_knowledge() -> None:
    client.post("/knowledge/ingest", json={"text": "The ocean is deep and vast.", "source_type": "text"})
    resp = client.post("/knowledge/query", json={"query": "ocean"})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data


def test_evidence_link() -> None:
    ingest_resp = client.post("/knowledge/ingest", json={"text": "The sky is blue. The sky is always blue.", "source_type": "text"})
    source_id = ingest_resp.json()["source_id"]
    extract_resp = client.post(f"/knowledge/extract/{source_id}")
    artifact_id = extract_resp.json()["artifact_id"]
    claims_resp = client.post(f"/knowledge/claims/{artifact_id}")
    claims = claims_resp.json()["claims"]
    if claims:
        claim_id = claims[0]["id"]
        resp = client.post(f"/knowledge/evidence/{claim_id}/{source_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "evidence_spans" in data


def test_score_claim_endpoint() -> None:
    ingest_resp = client.post("/knowledge/ingest", json={"text": "The sky is blue. The sky is always blue.", "source_type": "text"})
    source_id = ingest_resp.json()["source_id"]
    extract_resp = client.post(f"/knowledge/extract/{source_id}")
    artifact_id = extract_resp.json()["artifact_id"]
    claims_resp = client.post(f"/knowledge/claims/{artifact_id}")
    claims = claims_resp.json()["claims"]
    if claims:
        claim_id = claims[0]["id"]
        resp = client.post(f"/knowledge/score/{claim_id}/{source_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_score" in data


def test_provenance_endpoint() -> None:
    ingest_resp = client.post("/knowledge/ingest", json={"text": "Facts about climate change. It is very important.", "source_type": "text"})
    source_id = ingest_resp.json()["source_id"]
    extract_resp = client.post(f"/knowledge/extract/{source_id}")
    artifact_id = extract_resp.json()["artifact_id"]
    claims_resp = client.post(f"/knowledge/claims/{artifact_id}")
    claims = claims_resp.json()["claims"]
    if claims:
        claim_id = claims[0]["id"]
        resp = client.get(f"/knowledge/provenance/{claim_id}")
        assert resp.status_code == 200


def test_provenance_not_found() -> None:
    resp = client.get("/knowledge/provenance/nonexistent-id")
    assert resp.status_code == 404


def test_contradictions_endpoint() -> None:
    ingest_resp = client.post("/knowledge/ingest", json={"text": "Scientific evidence is important. Research matters a lot.", "source_type": "text"})
    source_id = ingest_resp.json()["source_id"]
    extract_resp = client.post(f"/knowledge/extract/{source_id}")
    artifact_id = extract_resp.json()["artifact_id"]
    claims_resp = client.post(f"/knowledge/claims/{artifact_id}")
    claims = claims_resp.json()["claims"]
    if claims:
        claim_id = claims[0]["id"]
        resp = client.get(f"/knowledge/contradictions/{claim_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0


def test_contradictions_not_found() -> None:
    resp = client.get("/knowledge/contradictions/nonexistent-id")
    assert resp.status_code == 404
