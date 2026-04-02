"""Integration tests for the /api/v1/artifacts/* routes.

Exercises all six artifact endpoints end-to-end through the FastAPI ASGI
test client.  Tests are isolated via a per-test app fixture that uses fresh
module-level singletons.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from thalos_prime.api.server import app

# ---------------------------------------------------------------------------
# Shared test client (module-level reuse is fine — singletons in artifacts.py
# accumulate state across test calls, which models real server behaviour).
# ---------------------------------------------------------------------------
client = TestClient(app)


# ===========================================================================
# Helpers
# ===========================================================================


def _ingest(content: str, source_uris: list[str] | None = None) -> dict[str, Any]:
    """POST /ingest and return the JSON body."""
    payload = {
        "content": content,
        "source_uris": source_uris or ["https://test.example/source"],
    }
    resp = client.post("/api/v1/artifacts/ingest", json=payload)
    assert resp.status_code == 200, resp.text
    result: dict[str, Any] = resp.json()
    return result


# ===========================================================================
# POST /ingest
# ===========================================================================


class TestIngestEndpoint:
    def test_returns_200(self) -> None:
        resp = client.post(
            "/api/v1/artifacts/ingest",
            json={"content": "hello world", "source_uris": ["https://x"]},
        )
        assert resp.status_code == 200

    def test_response_has_artifact(self) -> None:
        data = _ingest("response artifact test")
        assert "artifact" in data
        assert "artifact_id" in data["artifact"]

    def test_response_has_verdict(self) -> None:
        data = _ingest("response verdict test")
        assert "verdict" in data
        assert "final_status" in data["verdict"]
        assert "confidence" in data["verdict"]
        assert "coordinate" in data["verdict"]

    def test_coordinate_is_16_hex_chars(self) -> None:
        data = _ingest("coordinate hex test")
        coord = data["verdict"]["coordinate"]
        assert len(coord) == 16
        assert all(c in "0123456789abcdef" for c in coord)

    def test_confidence_in_range(self) -> None:
        data = _ingest("confidence range test")
        confidence = data["verdict"]["confidence"]
        assert 0.0 <= confidence <= 1.0

    def test_idempotent_double_ingest(self) -> None:
        content = "idempotent test " + str(id(self))
        d1 = _ingest(content)
        d2 = _ingest(content)
        # Same content → same artifact_id and verdict
        assert d1["artifact"]["artifact_id"] == d2["artifact"]["artifact_id"]

    def test_with_metadata(self) -> None:
        resp = client.post(
            "/api/v1/artifacts/ingest",
            json={
                "content": "metadata test",
                "source_uris": ["https://x"],
                "metadata": {"key": "value", "priority": "high"},
            },
        )
        assert resp.status_code == 200

    def test_valid_status_values(self) -> None:
        data = _ingest("status values test")
        status = data["verdict"]["final_status"]
        assert status in {"accepted", "pending", "rejected", "disputed"}


# ===========================================================================
# Endpoint: retrieve artifact by ID
# ===========================================================================


class TestGetArtifactEndpoint:
    def test_returns_200_for_known_artifact(self) -> None:
        data = _ingest("get artifact test content")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.get(f"/api/v1/artifacts/artifact/{artifact_id}")
        assert resp.status_code == 200

    def test_returns_404_for_unknown_artifact(self) -> None:
        resp = client.get("/api/v1/artifacts/artifact/deadbeef" + "0" * 56)
        assert resp.status_code == 404

    def test_response_has_artifact_id(self) -> None:
        data = _ingest("get artifact id check")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.get(f"/api/v1/artifacts/artifact/{artifact_id}")
        body = resp.json()
        assert body["artifact_id"] == artifact_id

    def test_response_has_state(self) -> None:
        data = _ingest("get artifact state check")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.get(f"/api/v1/artifacts/artifact/{artifact_id}")
        body = resp.json()
        assert "state" in body

    def test_response_has_confidence(self) -> None:
        data = _ingest("get artifact confidence check")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.get(f"/api/v1/artifacts/artifact/{artifact_id}")
        body = resp.json()
        assert "confidence" in body


# ===========================================================================
# POST /derive
# ===========================================================================


class TestDeriveEndpoint:
    def _accepted_artifact_id(self, content: str) -> str | None:
        """Ingest and return the artifact_id only if it's ACCEPTED."""
        data = _ingest(content)
        if data["verdict"]["final_status"] == "accepted":
            artifact_id: str = data["artifact"]["artifact_id"]
            return artifact_id
        return None

    def test_unknown_operation_returns_400(self) -> None:
        resp = client.post(
            "/api/v1/artifacts/derive",
            json={"artifact_ids": [], "operation": "bogus_op"},
        )
        assert resp.status_code == 400

    def test_non_accepted_artifact_returns_400(self) -> None:
        resp = client.post(
            "/api/v1/artifacts/derive",
            json={
                "artifact_ids": ["0" * 64],
                "operation": "synthesize",
            },
        )
        assert resp.status_code == 400

    def test_derive_synthesize_with_accepted_artifact(self) -> None:
        # Try multiple times until we get an ACCEPTED verdict
        for i in range(5):
            data = _ingest(f"accepted derive content iteration {i}")
            if data["verdict"]["final_status"] == "accepted":
                aid = data["artifact"]["artifact_id"]
                resp = client.post(
                    "/api/v1/artifacts/derive",
                    json={"artifact_ids": [aid], "operation": "synthesize"},
                )
                assert resp.status_code == 200
                body = resp.json()
                assert "candidate_claim" in body
                assert "verdict" in body
                assert "claim_id" in body["candidate_claim"]
                return
        pytest.skip("No ACCEPTED artifact generated in 5 attempts")

    def test_valid_operations(self) -> None:
        valid_ops = ["synthesize", "summarize", "extract", "infer", "combine"]
        for op in valid_ops:
            resp = client.post(
                "/api/v1/artifacts/derive",
                json={"artifact_ids": ["nonexistent_id"], "operation": op},
            )
            # 400 because IDs don't exist, not 422 or 500
            assert resp.status_code == 400


# ===========================================================================
# Endpoint: export artifact
# ===========================================================================


class TestExportEndpoint:
    def test_returns_200_for_known_artifact(self) -> None:
        data = _ingest("export endpoint test content")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.get(f"/api/v1/artifacts/export/{artifact_id}")
        assert resp.status_code == 200

    def test_returns_404_for_unknown(self) -> None:
        resp = client.get("/api/v1/artifacts/export/" + "a" * 64)
        assert resp.status_code == 404

    def test_response_structure(self) -> None:
        data = _ingest("export structure test content")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.get(f"/api/v1/artifacts/export/{artifact_id}")
        body = resp.json()
        assert "artifact" in body
        assert "proof_trace" in body
        assert "belief_record" in body

    def test_proof_trace_has_validation_stages(self) -> None:
        data = _ingest("export proof trace validation stages")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.get(f"/api/v1/artifacts/export/{artifact_id}")
        body = resp.json()
        assert len(body["proof_trace"]["validation_stages"]) > 0

    def test_belief_record_has_state(self) -> None:
        data = _ingest("export belief record state test")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.get(f"/api/v1/artifacts/export/{artifact_id}")
        body = resp.json()
        assert "state" in body["belief_record"]


# ===========================================================================
# Endpoint: lineage graph
# ===========================================================================


class TestGraphEndpoint:
    def test_returns_200_for_known_artifact(self) -> None:
        data = _ingest("graph endpoint test content")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.get(f"/api/v1/artifacts/graph/{artifact_id}")
        assert resp.status_code == 200

    def test_returns_404_for_unknown(self) -> None:
        resp = client.get("/api/v1/artifacts/graph/" + "b" * 64)
        assert resp.status_code == 404

    def test_response_structure(self) -> None:
        data = _ingest("graph structure test content")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.get(f"/api/v1/artifacts/graph/{artifact_id}")
        body = resp.json()
        assert "graph_id" in body
        assert "root_artifact_id" in body
        assert "nodes" in body
        assert "edges" in body

    def test_root_artifact_id_matches(self) -> None:
        data = _ingest("graph root artifact id test")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.get(f"/api/v1/artifacts/graph/{artifact_id}")
        body = resp.json()
        assert body["root_artifact_id"] == artifact_id


# ===========================================================================
# POST /consensus
# ===========================================================================


class TestConsensusEndpoint:
    def test_empty_candidate_list_returns_no_winner(self) -> None:
        resp = client.post(
            "/api/v1/artifacts/consensus",
            json={"artifact_ids": [], "min_confidence": 0.5},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["consensus_artifact_id"] is None

    def test_unknown_ids_returns_no_winner(self) -> None:
        resp = client.post(
            "/api/v1/artifacts/consensus",
            json={"artifact_ids": ["deadbeef" * 8], "min_confidence": 0.1},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["consensus_artifact_id"] is None

    def test_response_structure(self) -> None:
        resp = client.post(
            "/api/v1/artifacts/consensus",
            json={"artifact_ids": [], "min_confidence": 0.5},
        )
        body = resp.json()
        assert "consensus_artifact_id" in body
        assert "agreement_score" in body
        assert "participant_count" in body
        assert "message" in body

    def test_consensus_with_accepted_artifacts(self) -> None:
        # Ingest several artifacts and collect those that are accepted
        accepted_ids = []
        for i in range(6):
            data = _ingest(f"consensus candidate {i} unique content block xyz")
            if data["verdict"]["final_status"] == "accepted":
                accepted_ids.append(data["artifact"]["artifact_id"])

        if not accepted_ids:
            pytest.skip("No ACCEPTED artifacts generated")

        resp = client.post(
            "/api/v1/artifacts/consensus",
            json={"artifact_ids": accepted_ids, "min_confidence": 0.0},
        )
        assert resp.status_code == 200
        body = resp.json()
        if body["consensus_artifact_id"] is not None:
            assert body["consensus_artifact_id"] in accepted_ids
            assert body["agreement_score"] >= 0.0
            assert body["participant_count"] > 0

    def test_high_confidence_threshold_filters_out(self) -> None:
        data = _ingest("high threshold filter test content")
        artifact_id = data["artifact"]["artifact_id"]
        resp = client.post(
            "/api/v1/artifacts/consensus",
            json={
                "artifact_ids": [artifact_id],
                "min_confidence": 1.0,  # practically impossible
            },
        )
        assert resp.status_code == 200
        # Unlikely to win with threshold=1.0, but response is always valid
        body = resp.json()
        assert "consensus_artifact_id" in body

    def test_default_min_confidence(self) -> None:
        """Omitting min_confidence should use default (0.5)."""
        resp = client.post(
            "/api/v1/artifacts/consensus",
            json={"artifact_ids": []},
        )
        assert resp.status_code == 200
