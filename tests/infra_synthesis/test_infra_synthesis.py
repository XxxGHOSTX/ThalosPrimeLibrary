"""Tests for infra-synthesis: schema validation, engine, hasher, drift, policy, RBAC."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_SCHEMA: dict[str, Any] = {
    "project": {"name": "test-project", "version": "1.0.0"},
    "compute": {"type": "container", "scaling": 3},
    "network": {"protocol": "https", "region": "us-east-1"},
    "storage": {"backend": "s3"},
    "ci": {"provider": "github_actions", "release_strategy": "direct"},
}


# ---------------------------------------------------------------------------
# SchemaLoader tests
# ---------------------------------------------------------------------------


class TestSchemaLoader:
    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        from thalos_prime.infra_synthesis.schema_loader import SchemaLoader

        schema_file = tmp_path / "test.yaml"
        schema_file.write_text(
            "project:\n  name: hello\n  version: '1.0.0'\n", encoding="utf-8"
        )
        loader = SchemaLoader()
        result = loader.load(schema_file)
        assert result["project"]["name"] == "hello"

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        from thalos_prime.infra_synthesis.schema_loader import SchemaLoader, SchemaLoadError

        loader = SchemaLoader()
        with pytest.raises(SchemaLoadError, match="not found"):
            loader.load(tmp_path / "nonexistent.yaml")

    def test_load_invalid_yaml_raises(self, tmp_path: Path) -> None:
        from thalos_prime.infra_synthesis.schema_loader import SchemaLoader, SchemaLoadError

        schema_file = tmp_path / "bad.yaml"
        schema_file.write_text("key: [unclosed", encoding="utf-8")
        loader = SchemaLoader()
        with pytest.raises(SchemaLoadError, match="YAML parse error"):
            loader.load(schema_file)

    def test_load_non_mapping_raises(self, tmp_path: Path) -> None:
        from thalos_prime.infra_synthesis.schema_loader import SchemaLoader, SchemaLoadError

        schema_file = tmp_path / "list.yaml"
        schema_file.write_text("- item1\n- item2\n", encoding="utf-8")
        loader = SchemaLoader()
        with pytest.raises(SchemaLoadError, match="mapping"):
            loader.load(schema_file)


# ---------------------------------------------------------------------------
# SchemaValidator tests
# ---------------------------------------------------------------------------


class TestSchemaValidator:
    def test_valid_schema_passes(self) -> None:
        from thalos_prime.infra_synthesis.validator import SchemaValidator

        validator = SchemaValidator()
        result = validator.validate(VALID_SCHEMA)
        assert result.valid is True
        assert result.violations == []

    def test_missing_section_fails(self) -> None:
        from thalos_prime.infra_synthesis.validator import SchemaValidator

        validator = SchemaValidator()
        schema = {k: v for k, v in VALID_SCHEMA.items() if k != "storage"}
        result = validator.validate(schema)
        assert result.valid is False
        assert any("storage" in v for v in result.violations)

    def test_invalid_compute_type_fails(self) -> None:
        from thalos_prime.infra_synthesis.validator import SchemaValidator

        validator = SchemaValidator()
        schema = {**VALID_SCHEMA, "compute": {"type": "quantum"}}
        result = validator.validate(schema)
        assert result.valid is False
        assert any("compute.type" in v for v in result.violations)

    def test_invalid_protocol_fails(self) -> None:
        from thalos_prime.infra_synthesis.validator import SchemaValidator

        validator = SchemaValidator()
        schema = {**VALID_SCHEMA, "network": {"protocol": "ftp"}}
        result = validator.validate(schema)
        assert result.valid is False
        assert any("network.protocol" in v for v in result.violations)

    def test_scaling_zero_fails(self) -> None:
        from thalos_prime.infra_synthesis.validator import SchemaValidator

        validator = SchemaValidator()
        schema = {**VALID_SCHEMA, "compute": {"type": "container", "scaling": 0}}
        result = validator.validate(schema)
        assert result.valid is False

    def test_all_required_sections_missing(self) -> None:
        from thalos_prime.infra_synthesis.validator import SchemaValidator

        validator = SchemaValidator()
        result = validator.validate({})
        assert result.valid is False
        assert len(result.violations) == 5  # all 5 sections missing


# ---------------------------------------------------------------------------
# InfraSynthesisEngine tests
# ---------------------------------------------------------------------------


class TestInfraSynthesisEngine:
    def _write_schema(self, tmp_path: Path, schema: dict[str, Any] | None = None) -> Path:
        import yaml

        data = schema or VALID_SCHEMA
        schema_file = tmp_path / "infra.schema.yaml"
        schema_file.write_text(yaml.dump(data), encoding="utf-8")
        return schema_file

    def test_generate_creates_artifacts(self, tmp_path: Path) -> None:
        from thalos_prime.infra_synthesis.engine import InfraSynthesisEngine

        schema_file = self._write_schema(tmp_path)
        out_dir = tmp_path / "dist"
        engine = InfraSynthesisEngine()
        result = engine.generate(schema_path=schema_file, out_dir=out_dir)

        assert result.out_dir == out_dir
        assert len(result.artifacts) > 0
        # Terraform
        assert (out_dir / "terraform" / "main.tf").exists()
        assert (out_dir / "terraform" / "provider.tf").exists()
        # OpenTofu
        assert (out_dir / "opentofu" / "main.tf").exists()
        # Cloudflare
        assert (out_dir / "wrangler.toml").exists()
        # GitHub Actions
        assert (out_dir / "ci.yml").exists()
        # Docker output when compute type is container
        assert (out_dir / "Dockerfile").exists()

    def test_generate_writes_manifest(self, tmp_path: Path) -> None:
        from thalos_prime.infra_synthesis.engine import InfraSynthesisEngine

        schema_file = self._write_schema(tmp_path)
        out_dir = tmp_path / "dist"
        engine = InfraSynthesisEngine()
        engine.generate(schema_path=schema_file, out_dir=out_dir)

        manifest_path = out_dir / "artifact_manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "artifacts" in manifest
        assert len(manifest["artifacts"]) > 0

    def test_generate_raises_on_invalid_schema(self, tmp_path: Path) -> None:
        from thalos_prime.infra_synthesis.engine import InfraSynthesisEngine

        bad_schema = {"project": {"name": "x", "version": "1"}, "compute": {"type": "bad"}}
        schema_file = self._write_schema(tmp_path, bad_schema)
        engine = InfraSynthesisEngine()
        with pytest.raises(ValueError, match="validation failed"):
            engine.generate(schema_path=schema_file, out_dir=tmp_path / "dist")

    def test_event_bus_emits_generated_and_hashed(self, tmp_path: Path) -> None:
        from thalos_prime.infra_synthesis.engine import InfraSynthesisEngine

        schema_file = self._write_schema(tmp_path)
        out_dir = tmp_path / "dist"
        engine = InfraSynthesisEngine()
        events_seen: list[str] = []
        engine.event_bus.subscribe("generated", lambda e, _p: events_seen.append(e))
        engine.event_bus.subscribe("hashed", lambda e, _p: events_seen.append(e))
        engine.generate(schema_path=schema_file, out_dir=out_dir)

        assert "generated" in events_seen
        assert "hashed" in events_seen

    def test_docker_adapter_skipped_for_serverless(self, tmp_path: Path) -> None:
        from thalos_prime.infra_synthesis.engine import InfraSynthesisEngine

        schema = {**VALID_SCHEMA, "compute": {"type": "serverless", "scaling": 1}}
        schema_file = self._write_schema(tmp_path, schema)
        out_dir = tmp_path / "dist"
        engine = InfraSynthesisEngine()
        result = engine.generate(schema_path=schema_file, out_dir=out_dir)

        # Dockerfile must NOT be generated for serverless
        assert not (out_dir / "Dockerfile").exists()
        artifact_names = [a.name for a in result.artifacts]
        assert "Dockerfile" not in artifact_names


# ---------------------------------------------------------------------------
# Hasher tests
# ---------------------------------------------------------------------------


class TestHasher:
    def test_sha256_file(self, tmp_path: Path) -> None:
        import hashlib

        from thalos_prime.infra_synthesis.hasher import Hasher

        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert Hasher.sha256_file(test_file) == expected

    def test_hash_artifacts_writes_manifest(self, tmp_path: Path) -> None:
        from thalos_prime.infra_synthesis.hasher import Hasher

        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.txt"
            f.write_text(f"content {i}", encoding="utf-8")
            files.append(f)

        hasher = Hasher()
        manifest = hasher.hash_artifacts(files, tmp_path)

        assert len(manifest) == 3
        manifest_path = tmp_path / "artifact_manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert len(data["artifacts"]) == 3

    def test_hash_is_deterministic(self, tmp_path: Path) -> None:
        from thalos_prime.infra_synthesis.hasher import Hasher

        f = tmp_path / "deterministic.txt"
        f.write_bytes(b"fixed content")
        h1 = Hasher.sha256_file(f)
        h2 = Hasher.sha256_file(f)
        assert h1 == h2


# ---------------------------------------------------------------------------
# DriftDetector tests
# ---------------------------------------------------------------------------


class TestDriftDetector:
    def test_no_drift(self) -> None:
        from thalos_prime.infra_synthesis.drift import DriftDetector

        detector = DriftDetector()
        result = detector.detect(VALID_SCHEMA, dict(VALID_SCHEMA))
        assert result.drifted is False
        assert result.diff == {}

    def test_drift_detected(self) -> None:
        from thalos_prime.infra_synthesis.drift import DriftDetector

        detector = DriftDetector()
        live = {**VALID_SCHEMA, "compute": {"type": "serverless", "scaling": 1}}
        result = detector.detect(VALID_SCHEMA, live)
        assert result.drifted is True
        assert result.diff != {}

    def test_drift_summary_contains_change_count(self) -> None:
        from thalos_prime.infra_synthesis.drift import DriftDetector

        detector = DriftDetector()
        live = {**VALID_SCHEMA, "network": {"protocol": "http", "region": "eu-west-1"}}
        result = detector.detect(VALID_SCHEMA, live)
        assert "Drift detected" in result.summary


# ---------------------------------------------------------------------------
# PolicyEngine tests
# ---------------------------------------------------------------------------


class TestPolicyEngine:
    def test_require_ssl_passes(self) -> None:
        from thalos_prime.infra_synthesis.policy.engine import PolicyEngine

        engine = PolicyEngine()
        result = engine.evaluate(VALID_SCHEMA, rules=["require_ssl"])
        assert result.passed is True

    def test_require_ssl_fails_on_http(self) -> None:
        from thalos_prime.infra_synthesis.policy.engine import PolicyEngine

        schema = {**VALID_SCHEMA, "network": {"protocol": "http"}}
        engine = PolicyEngine()
        result = engine.evaluate(schema, rules=["require_ssl"])
        assert result.passed is False

    def test_limit_scaling_passes_within_limit(self) -> None:
        from thalos_prime.infra_synthesis.policy.engine import PolicyEngine

        engine = PolicyEngine()
        result = engine.evaluate(VALID_SCHEMA, rules=["limit_scaling"])
        assert result.passed is True

    def test_limit_scaling_fails_above_50(self) -> None:
        from thalos_prime.infra_synthesis.policy.engine import PolicyEngine

        schema = {**VALID_SCHEMA, "compute": {"type": "container", "scaling": 51}}
        engine = PolicyEngine()
        result = engine.evaluate(schema, rules=["limit_scaling"])
        assert result.passed is False

    def test_unknown_rule_raises(self) -> None:
        from thalos_prime.infra_synthesis.policy.engine import PolicyEngine

        engine = PolicyEngine()
        with pytest.raises(KeyError, match="not registered"):
            engine.evaluate(VALID_SCHEMA, rules=["nonexistent_rule"])

    def test_all_rules_evaluate(self) -> None:
        from thalos_prime.infra_synthesis.policy.engine import PolicyEngine

        engine = PolicyEngine()
        result = engine.evaluate(VALID_SCHEMA)
        assert len(result.results) >= 2  # at least the two built-in rules


# ---------------------------------------------------------------------------
# RBAC tests
# ---------------------------------------------------------------------------


class TestRBAC:
    def test_admin_has_all_permissions(self) -> None:
        from thalos_prime.infra_synthesis.security.rbac import ROLE_MAP, check

        for permission in ROLE_MAP["admin"]:
            assert check("admin", permission) is True

    def test_developer_cannot_deploy(self) -> None:
        from thalos_prime.infra_synthesis.security.rbac import check

        assert check("developer", "deploy") is False

    def test_devops_can_deploy(self) -> None:
        from thalos_prime.infra_synthesis.security.rbac import check

        assert check("devops", "deploy") is True

    def test_unknown_role_denied(self) -> None:
        from thalos_prime.infra_synthesis.security.rbac import check

        assert check("anonymous", "build") is False

    def test_developer_can_build_and_verify(self) -> None:
        from thalos_prime.infra_synthesis.security.rbac import check

        assert check("developer", "build") is True
        assert check("developer", "verify") is True


# ---------------------------------------------------------------------------
# Integration: load real schema and run engine
# ---------------------------------------------------------------------------


class TestRealSchemaIntegration:
    def test_load_and_generate_sample_schema(self, tmp_path: Path) -> None:
        """Full pipeline: load schemas/infra.schema.yaml and generate artifacts."""
        from thalos_prime.infra_synthesis.engine import InfraSynthesisEngine

        repo_root = Path(__file__).parent.parent.parent
        schema_path = repo_root / "schemas" / "infra.schema.yaml"
        if not schema_path.exists():
            pytest.skip("schemas/infra.schema.yaml not found")

        out_dir = tmp_path / "dist"
        engine = InfraSynthesisEngine()
        result = engine.generate(schema_path=schema_path, out_dir=out_dir)

        assert (out_dir / "artifact_manifest.json").exists()
        assert (out_dir / "wrangler.toml").exists()
        assert (out_dir / "ci.yml").exists()
        assert (out_dir / "terraform" / "main.tf").exists()
        assert (out_dir / "opentofu" / "main.tf").exists()
        assert (out_dir / "Dockerfile").exists()
        assert len(result.manifest) > 0
