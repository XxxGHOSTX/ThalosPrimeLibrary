"""Integration tests for graph and library API routes using FastAPI TestClient."""

from __future__ import annotations

from fastapi.testclient import TestClient

from thalos_prime.api.server import app


class TestGraphExecuteEndpoint:
    """Integration tests for POST /api/v1/graph/execute."""

    def test_execute_returns_200_with_graph_id(self) -> None:
        """Execute endpoint returns HTTP 200 and a graph_id."""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/graph/execute",
                json={"query": "test", "mode": "fast"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "graph_id" in data
        assert isinstance(data["graph_id"], str)
        assert len(data["graph_id"]) > 0

    def test_execute_returns_graph_hash(self) -> None:
        """Execute endpoint returns a non-empty graph_hash."""
        with TestClient(app) as client:
            response = client.post("/api/v1/graph/execute", json={"x": 1})
        assert response.status_code == 200
        assert "graph_hash" in response.json()

    def test_execute_returns_outputs(self) -> None:
        """Execute endpoint returns an outputs dict."""
        with TestClient(app) as client:
            response = client.post("/api/v1/graph/execute", json={"payload": "hello"})
        assert response.status_code == 200
        data = response.json()
        assert "outputs" in data
        assert isinstance(data["outputs"], dict)


class TestGraphGetEndpoint:
    """Integration tests for GET /api/v1/graph/{graph_id}."""

    def test_get_graph_returns_200_for_existing(self) -> None:
        """GET /graph/{id} returns 200 for a graph that was previously executed."""
        with TestClient(app) as client:
            exec_resp = client.post("/api/v1/graph/execute", json={"x": 42})
            graph_id = exec_resp.json()["graph_id"]
            response = client.get(f"/api/v1/graph/{graph_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == graph_id

    def test_get_graph_returns_404_for_missing(self) -> None:
        """GET /graph/{id} returns 404 for an unknown graph ID."""
        with TestClient(app) as client:
            response = client.get("/api/v1/graph/nonexistent-graph-id-xyz")
        assert response.status_code == 404


class TestGraphReplayEndpoint:
    """Integration tests for POST /api/v1/graph/{graph_id}/replay."""

    def test_replay_returns_200(self) -> None:
        """Replay endpoint returns HTTP 200 for a valid graph."""
        with TestClient(app) as client:
            exec_resp = client.post("/api/v1/graph/execute", json={"x": 1})
            graph_id = exec_resp.json()["graph_id"]
            response = client.post(f"/api/v1/graph/{graph_id}/replay")
        assert response.status_code == 200

    def test_replay_returns_graph_id_and_hash(self) -> None:
        """Replay endpoint returns graph_id and graph_hash."""
        with TestClient(app) as client:
            exec_resp = client.post("/api/v1/graph/execute", json={"key": "val"})
            graph_id = exec_resp.json()["graph_id"]
            response = client.post(f"/api/v1/graph/{graph_id}/replay")
        assert response.status_code == 200
        data = response.json()
        assert "graph_id" in data
        assert "graph_hash" in data

    def test_replay_404_for_missing_graph(self) -> None:
        """Replay endpoint returns 404 for an unknown graph ID."""
        with TestClient(app) as client:
            response = client.post("/api/v1/graph/no-such-graph/replay")
        assert response.status_code == 404


class TestGraphProvenanceEndpoint:
    """Integration tests for GET /api/v1/graph/{graph_id}/provenance."""

    def test_provenance_returns_200(self) -> None:
        """Provenance endpoint returns HTTP 200."""
        with TestClient(app) as client:
            exec_resp = client.post("/api/v1/graph/execute", json={"data": "prov"})
            graph_id = exec_resp.json()["graph_id"]
            response = client.get(f"/api/v1/graph/{graph_id}/provenance")
        assert response.status_code == 200

    def test_provenance_returns_records(self) -> None:
        """Provenance endpoint returns a list of records."""
        with TestClient(app) as client:
            exec_resp = client.post("/api/v1/graph/execute", json={"data": "prov2"})
            graph_id = exec_resp.json()["graph_id"]
            response = client.get(f"/api/v1/graph/{graph_id}/provenance")
        data = response.json()
        assert "records" in data
        assert isinstance(data["records"], list)


class TestLibraryReconstructEndpoint:
    """Integration tests for POST /api/v1/library/reconstruct."""

    def test_reconstruct_returns_200(self) -> None:
        """Reconstruct endpoint returns HTTP 200."""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/library/reconstruct",
                json={"text": "hello world from the library"},
            )
        assert response.status_code == 200

    def test_reconstruct_returns_artifacts(self) -> None:
        """Reconstruct endpoint returns a list of artifacts."""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/library/reconstruct",
                json={"text": "the quick brown fox jumps over the lazy dog"},
            )
        data = response.json()
        assert "artifacts" in data
        assert isinstance(data["artifacts"], list)
        assert len(data["artifacts"]) >= 1

    def test_reconstruct_422_for_missing_text(self) -> None:
        """Reconstruct endpoint returns 422 when text field is missing."""
        with TestClient(app) as client:
            response = client.post("/api/v1/library/reconstruct", json={})
        assert response.status_code == 422


class TestLibraryArtifactEndpoint:
    """Integration tests for GET /api/v1/library/artifacts/{id}."""

    def test_get_artifact_200_for_stored(self) -> None:
        """GET artifact returns 200 for a previously reconstructed artifact."""
        with TestClient(app) as client:
            recon_resp = client.post(
                "/api/v1/library/reconstruct",
                json={"text": "unique artifact content for retrieval test"},
            )
            artifacts = recon_resp.json()["artifacts"]
            assert artifacts
            artifact_id = artifacts[0]["id"]
            response = client.get(f"/api/v1/library/artifacts/{artifact_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == artifact_id

    def test_get_artifact_404_for_missing(self) -> None:
        """GET artifact returns 404 for an unknown artifact ID."""
        with TestClient(app) as client:
            response = client.get("/api/v1/library/artifacts/nonexistent-artifact-id")
        assert response.status_code == 404
