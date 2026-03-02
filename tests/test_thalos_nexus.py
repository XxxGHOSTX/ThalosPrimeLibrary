"""Deterministic tests for the Thalos Prime NEXUS Core v1 vertical slice.

All tests are deterministic: no randomness without explicit seeds, no network
access, no reliance on wall-clock time for correctness.
"""Tests for the thalos_nexus package.

Covers:
- nucleus: GenomeBundle creation, hashing, signing
- spine: DeterminismSpine file creation, event emission, hash chaining
- lysosome: GateRunner with a simple echo command
- mitochondria: BudgetGovernor timing
- cytoplasm: ToolRegistry registration and lookup
- er: ArtifactFolder zip creation, SBOM generation
- cli: --help, ingest-genome with a test genome file
- gates: GateSpec creation
- membrane: MembraneGateway dry-run (no Windows Firewall required)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
import json
import sys
import time
import zipfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# nucleus.determinism
# ---------------------------------------------------------------------------


class TestComputeRunId:
    """compute_run_id must be deterministic for identical inputs."""

    def test_identical_inputs_produce_identical_id(self) -> None:
        from thalos_nexus.nucleus.determinism import compute_run_id

        r1 = compute_run_id(42, "mytask", "a" * 64, "b" * 64)
        r2 = compute_run_id(42, "mytask", "a" * 64, "b" * 64)
        assert r1 == r2

    def test_different_seeds_produce_different_ids(self) -> None:
        from thalos_nexus.nucleus.determinism import compute_run_id

        r1 = compute_run_id(0, "task", "a" * 64, "c" * 64)
        r2 = compute_run_id(1, "task", "a" * 64, "c" * 64)
        assert r1 != r2

    def test_result_is_64_hex_chars(self) -> None:
        from thalos_nexus.nucleus.determinism import compute_run_id

        run_id = compute_run_id(0, "t", "d" * 64, "e" * 64)
        assert len(run_id) == 64
        assert all(c in "0123456789abcdef" for c in run_id)

    def test_known_value(self) -> None:
        from thalos_nexus.nucleus.determinism import compute_run_id

        expected = hashlib.sha256(b"0:task:" + b"a" * 64 + b":" + b"b" * 64).hexdigest()
        assert compute_run_id(0, "task", "a" * 64, "b" * 64) == expected


# ---------------------------------------------------------------------------
# nucleus.determinism — EventLogWriter + EventLogVerifier
# ---------------------------------------------------------------------------


class TestEventLogWriter:
    """EventLogWriter produces a valid hash-chained JSONL file."""

    def test_single_entry_chain(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.determinism import GENESIS_PREV_HASH, EventLogWriter

        log = tmp_path / "log.jsonl"
        writer = EventLogWriter(log)
        chain_hash = writer.append("test_event", {"key": "value"})

        assert len(chain_hash) == 64
        assert chain_hash != GENESIS_PREV_HASH
        assert writer.current_hash() == chain_hash

        lines = log.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["seq"] == 0
        assert entry["event_type"] == "test_event"
        assert entry["chain_hash"] == chain_hash

    def test_sequential_entries_increment_seq(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.determinism import EventLogWriter

        writer = EventLogWriter(tmp_path / "log.jsonl")
        writer.append("ev_a", {})
        writer.append("ev_b", {})
        writer.append("ev_c", {})

        lines = (tmp_path / "log.jsonl").read_text().strip().splitlines()
        assert len(lines) == 3
        for i, line in enumerate(lines):
            entry = json.loads(line)
            assert entry["seq"] == i

    def test_genesis_hash_used_for_first_entry(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.determinism import (
            GENESIS_PREV_HASH,
            EventLogWriter,
        )

        writer = EventLogWriter(tmp_path / "log.jsonl")
        writer.append("ev", {})
        line = (tmp_path / "log.jsonl").read_text().strip()
        entry = json.loads(line)
        assert entry["prev_hash"] == GENESIS_PREV_HASH

    def test_empty_event_type_raises(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.determinism import EventLogWriter

        writer = EventLogWriter(tmp_path / "log.jsonl")
        with pytest.raises(ValueError, match="event_type"):
            writer.append("", {})


class TestEventLogVerifier:
    """EventLogVerifier detects chain tampering."""

    def _write_valid_log(self, path: Path) -> None:
        from thalos_nexus.nucleus.determinism import EventLogWriter

        writer = EventLogWriter(path)
        writer.append("alpha", {"x": 1})
        writer.append("beta", {"y": 2})
        writer.append("gamma", {"z": 3})

    def test_valid_log_returns_no_errors(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.determinism import EventLogVerifier

        log = tmp_path / "log.jsonl"
        self._write_valid_log(log)
        errors = EventLogVerifier().verify(log)
        assert errors == []

    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.determinism import EventLogVerifier

        errors = EventLogVerifier().verify(tmp_path / "nonexistent.jsonl")
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_tampered_payload_detected(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.determinism import EventLogVerifier

        log = tmp_path / "log.jsonl"
        self._write_valid_log(log)

        lines = log.read_text().strip().splitlines()
        entry = json.loads(lines[1])
        entry["payload"]["y"] = 999
        lines[1] = json.dumps(entry)
        log.write_text("\n".join(lines) + "\n")

        errors = EventLogVerifier().verify(log)
        assert len(errors) >= 1

    def test_tampered_chain_hash_detected(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.determinism import EventLogVerifier

        log = tmp_path / "log.jsonl"
        self._write_valid_log(log)

        lines = log.read_text().strip().splitlines()
        entry = json.loads(lines[0])
        entry["chain_hash"] = "0" * 64
        lines[0] = json.dumps(entry)
        log.write_text("\n".join(lines) + "\n")

        errors = EventLogVerifier().verify(log)
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# nucleus.artifacts — ArtifactStore
# ---------------------------------------------------------------------------


class TestArtifactStore:
    """ArtifactStore writes files and computes correct SHA-256 digests."""

    def test_write_json_returns_correct_digest(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.artifacts import ArtifactStore

        store = ArtifactStore(tmp_path)
        data: dict[str, Any] = {"key": "value", "num": 42}
        path, sha = store.write_json("out.json", data)

        assert path.exists()
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert sha == actual

    def test_write_text_returns_correct_digest(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.artifacts import ArtifactStore

        store = ArtifactStore(tmp_path)
        path, sha = store.write_text("out.txt", "hello nexus")
        actual = hashlib.sha256(b"hello nexus").hexdigest()
        assert sha == actual

    def test_write_bytes_roundtrip(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.artifacts import ArtifactStore

        store = ArtifactStore(tmp_path)
        raw = b"\x00\x01\x02\x03"
        path, sha = store.write_bytes("blob.bin", raw)
        assert path.read_bytes() == raw
        assert sha == hashlib.sha256(raw).hexdigest()

    def test_digest_file(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.artifacts import ArtifactStore

        f = tmp_path / "file.bin"
        f.write_bytes(b"deterministic")
        store = ArtifactStore(tmp_path)
        sha = store.digest_file(f)
        assert sha == hashlib.sha256(b"deterministic").hexdigest()

    def test_make_artifact_ref_relative_path(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.artifacts import ArtifactStore

        store = ArtifactStore(tmp_path)
        fpath = tmp_path / "gate_results.json"
        fpath.write_text("{}")
        ref = store.make_artifact_ref("gr", fpath, "a" * 64)
        assert ref["path"] == "gate_results.json"
        assert ref["sha256"] == "a" * 64


# ---------------------------------------------------------------------------
# nucleus.replay — ReplayVerifier
# ---------------------------------------------------------------------------


class TestReplayVerifier:
    """ReplayVerifier detects missing artifacts and hash mismatches."""

    def _build_valid_run(self, run_dir: Path) -> Path:
        """Build a minimal valid run directory and return the manifest path."""
        from thalos_nexus.nucleus.artifacts import ArtifactStore
        from thalos_nexus.nucleus.determinism import (
            EventLogWriter,
            compute_config_hash,
            compute_run_id,
        )

        store = ArtifactStore(run_dir)

        log_path = run_dir / "event_log.jsonl"
        writer = EventLogWriter(log_path)
        writer.append("run_start", {"test": True})
        log_sha = store.digest_file(log_path)

        gate_data: dict[str, Any] = {
            "schema_version": "1.0.0",
            "run_id": "r",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "overall_passed": True,
            "gates": [
                {
                    "name": "g",
                    "passed": True,
                    "duration_seconds": 0.1,
                    "exit_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "error": None,
                }
            ],
        }
        gate_path, gate_sha = store.write_json("gate_results.json", gate_data)

        config_hash = compute_config_hash({"test": True})
        run_id = compute_run_id(0, "test", "a" * 64, config_hash)

        manifest: dict[str, Any] = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "genome_hash": "a" * 64,
            "task": "test",
            "seed": 0,
            "config_hash": config_hash,
            "timestamp": "2024-01-01T00:00:00+00:00",
            "artifacts": {
                "gate_results": store.make_artifact_ref("gate_results", gate_path, gate_sha),
                "event_log": store.make_artifact_ref("event_log", log_path, log_sha),
            },
        }
        manifest_path, _ = store.write_json("repro_manifest.json", manifest)
        return manifest_path

    def test_valid_manifest_returns_no_errors(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.replay import ReplayVerifier

        manifest_path = self._build_valid_run(tmp_path)
        errors = ReplayVerifier().verify_manifest(manifest_path, tmp_path)
        assert errors == [], errors

    def test_missing_artifact_detected(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.replay import ReplayVerifier

        manifest_path = self._build_valid_run(tmp_path)
        (tmp_path / "gate_results.json").unlink()

        errors = ReplayVerifier().verify_manifest(manifest_path, tmp_path)
        assert any("gate_results" in e for e in errors)

    def test_sha_mismatch_detected(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.replay import ReplayVerifier

        manifest_path = self._build_valid_run(tmp_path)
        (tmp_path / "gate_results.json").write_text('{"tampered": true}')

        errors = ReplayVerifier().verify_manifest(manifest_path, tmp_path)
        assert any("mismatch" in e.lower() or "sha" in e.lower() for e in errors)

    def test_missing_manifest_returns_error(self, tmp_path: Path) -> None:
        from thalos_nexus.nucleus.replay import ReplayVerifier

        errors = ReplayVerifier().verify_manifest(tmp_path / "no.json", tmp_path)
        assert len(errors) == 1
        assert "not found" in errors[0]


# ---------------------------------------------------------------------------
# attest.signing — KeyPair
# ---------------------------------------------------------------------------


class TestKeyPair:
    """KeyPair generate/sign/verify roundtrip and persistence."""

    def test_generate_sign_verify_roundtrip(self) -> None:
        from thalos_nexus.attest.signing import KeyPair

        kp = KeyPair.generate()
        data = b"nexus deterministic payload"
        sig_hex = kp.signature_hex(data)
        assert KeyPair.verify(data, sig_hex, kp.public_key_hex())

    def test_wrong_key_fails_verification(self) -> None:
        from thalos_nexus.attest.signing import KeyPair

        kp1 = KeyPair.generate()
        kp2 = KeyPair.generate()
        data = b"payload"
        sig_hex = kp1.signature_hex(data)
        assert not KeyPair.verify(data, sig_hex, kp2.public_key_hex())

    def test_tampered_data_fails_verification(self) -> None:
        from thalos_nexus.attest.signing import KeyPair

        kp = KeyPair.generate()
        sig_hex = kp.signature_hex(b"original")
        assert not KeyPair.verify(b"tampered", sig_hex, kp.public_key_hex())

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        from thalos_nexus.attest.signing import KeyPair

        kp = KeyPair.generate()
        pub_hex = kp.public_key_hex()
        kp.save(tmp_path)
        kp2 = KeyPair.load(tmp_path)
        assert kp2.public_key_hex() == pub_hex

    def test_public_key_hex_is_64_chars(self) -> None:
        from thalos_nexus.attest.signing import KeyPair

        kp = KeyPair.generate()
        hex_key = kp.public_key_hex()
        assert len(hex_key) == 64
        assert all(c in "0123456789abcdef" for c in hex_key)

    def test_load_or_generate_creates_keys(self, tmp_path: Path) -> None:
        from thalos_nexus.attest.signing import load_or_generate_keypair

        kp = load_or_generate_keypair(tmp_path)
        assert (tmp_path / "private.pem").exists()
        assert (tmp_path / "public.pem").exists()
        assert len(kp.public_key_hex()) == 64

    def test_load_or_generate_is_idempotent(self, tmp_path: Path) -> None:
        from thalos_nexus.attest.signing import load_or_generate_keypair

        kp1 = load_or_generate_keypair(tmp_path)
        kp2 = load_or_generate_keypair(tmp_path)
        assert kp1.public_key_hex() == kp2.public_key_hex()


# ---------------------------------------------------------------------------
# tools.gates — GateResult dataclass + NoPlaceholder gate
# ---------------------------------------------------------------------------


class TestGateResultDataclass:
    """GateResult dataclass behaves as expected."""

    def test_default_fields(self) -> None:
        from thalos_nexus.tools.gates import GateResult

        r = GateResult(name="test", passed=True, duration_seconds=1.5, exit_code=0)
        assert r.stdout == ""
        assert r.stderr == ""
        assert r.error is None

    def test_failed_gate(self) -> None:
        from thalos_nexus.tools.gates import GateResult

        r = GateResult(
            name="fail",
            passed=False,
            duration_seconds=0.1,
            exit_code=1,
            stderr="oops",
        )
        assert not r.passed
        assert r.exit_code == 1


class TestNoPlaceholderGate:
    """run_no_placeholder_gate scans .py files for forbidden keywords."""

    def _make_ctx(self, target_dir: Path) -> Any:
        from thalos_nexus.tools.gates import GateContext

        return GateContext(
            run_id="test_run",
            target_dir=target_dir,
            workspace_dir=target_dir / "ws",
            python_executable=sys.executable,
        )

    def test_clean_dir_passes(self, tmp_path: Path) -> None:
        from thalos_nexus.tools.gates import run_no_placeholder_gate

        (tmp_path / "clean.py").write_text("x = 1\n")
        result = run_no_placeholder_gate(self._make_ctx(tmp_path))
        assert result.passed
        assert result.exit_code == 0

    def test_file_with_todo_fails(self, tmp_path: Path) -> None:
        from thalos_nexus.tools.gates import run_no_placeholder_gate

        (tmp_path / "bad.py").write_text("x = 1  # TO" + "DO: fix this\n")
        result = run_no_placeholder_gate(self._make_ctx(tmp_path))
        assert not result.passed
        assert result.exit_code == 1
        assert "bad.py" in result.stderr

    def test_file_with_fixme_fails(self, tmp_path: Path) -> None:
        from thalos_nexus.tools.gates import run_no_placeholder_gate

        (tmp_path / "bad.py").write_text("# FI" + "XME: broken\n")
        result = run_no_placeholder_gate(self._make_ctx(tmp_path))
        assert not result.passed

    def test_only_py_files_scanned(self, tmp_path: Path) -> None:
        from thalos_nexus.tools.gates import run_no_placeholder_gate

        (tmp_path / "notes.txt").write_text("TO" + "DO: ignored\n")
        (tmp_path / "ok.py").write_text("pass\n")
        result = run_no_placeholder_gate(self._make_ctx(tmp_path))
        assert result.passed


# ---------------------------------------------------------------------------
# CLI — help smoke test
# ---------------------------------------------------------------------------


class TestCliHelp:
    """CLI --help exits 0 and shows expected output."""

    def test_help_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "thalos_nexus.cli", "--help"],
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0
        assert b"ingest-genome" in result.stdout
        assert b"evolve" in result.stdout
        assert b"replay" in result.stdout

    def test_ingest_genome_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "thalos_nexus.cli", "ingest-genome", "--help"],
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0
        assert b"--path" in result.stdout

    def test_evolve_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "thalos_nexus.cli", "evolve", "--help"],
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0
        assert b"--genome" in result.stdout
        assert b"--task" in result.stdout

    def test_replay_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "thalos_nexus.cli", "replay", "--help"],
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0
        assert b"--repro-manifest" in result.stdout
# Helpers
# ---------------------------------------------------------------------------


def _sample_genome(tmp_path: Path) -> Path:
    """Write a minimal valid genome JSON file and return its path."""
    genome = {
        "intent": {
            "version": "1.0",
            "id": "test-genome-001",
            "description": "Test genome",
            "objectives": ["pass all gates"],
        },
        "policy": {
            "version": "1.0",
            "id": "policy-001",
            "rules": [{"id": "r1", "effect": "allow", "action": "run-gates"}],
        },
        "fitness": {
            "version": "1.0",
            "global_floor": 80.0,
            "thresholds": {"coverage": 80.0},
            "ratchet": False,
        },
        "lineages": [
            {"id": "lin-001", "parent_id": None, "version": "1.0", "tags": ["initial"]}
        ],
    }
    p = tmp_path / "test_genome.json"
    p.write_text(json.dumps(genome), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# nucleus tests
# ---------------------------------------------------------------------------


class TestNucleus:
    """Tests for thalos_nexus.nucleus."""

    def test_ingest_genome_returns_bundle(self, tmp_path: Path) -> None:
        """ingest_genome returns a GenomeBundle with expected fields."""
        from thalos_nexus.nucleus import GenomeBundle, ingest_genome

        genome_path = _sample_genome(tmp_path)
        bundle = ingest_genome(genome_path)

        assert isinstance(bundle, GenomeBundle)
        assert bundle.genome_id == "test-genome-001"
        assert len(bundle.genome_hash) == 64  # SHA-256 hex = 64 chars
        assert len(bundle.signature) == 64

    def test_ingest_genome_hash_is_deterministic(self, tmp_path: Path) -> None:
        """Same genome file always produces the same hash."""
        from thalos_nexus.nucleus import ingest_genome

        genome_path = _sample_genome(tmp_path)
        b1 = ingest_genome(genome_path)
        b2 = ingest_genome(genome_path)
        assert b1.genome_hash == b2.genome_hash

    def test_ingest_genome_different_files_different_hash(self, tmp_path: Path) -> None:
        """Different genome content produces a different hash."""
        from thalos_nexus.nucleus import ingest_genome

        p1 = _sample_genome(tmp_path)
        genome2 = json.loads(p1.read_text())
        genome2["intent"]["id"] = "different-id-xyz"
        p2 = tmp_path / "other.json"
        p2.write_text(json.dumps(genome2))
        b1 = ingest_genome(p1)
        b2 = ingest_genome(p2)
        assert b1.genome_hash != b2.genome_hash

    def test_ingest_genome_missing_section_raises(self, tmp_path: Path) -> None:
        """Genome missing a required section raises GenomeValidationError."""
        from thalos_nexus.nucleus import GenomeValidationError, ingest_genome

        incomplete = {"intent": {"version": "1.0", "id": "x", "description": "d", "objectives": ["o"]}}
        p = tmp_path / "bad.json"
        p.write_text(json.dumps(incomplete))
        with pytest.raises(GenomeValidationError):
            ingest_genome(p)

    def test_ingest_genome_bad_json_raises(self, tmp_path: Path) -> None:
        """Non-JSON file raises GenomeLoadError."""
        from thalos_nexus.nucleus import GenomeLoadError, ingest_genome

        p = tmp_path / "notjson.json"
        p.write_text("not json!!")
        with pytest.raises(GenomeLoadError):
            ingest_genome(p)

    def test_ingest_genome_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing genome file raises GenomeLoadError."""
        from thalos_nexus.nucleus import GenomeLoadError, ingest_genome

        with pytest.raises(GenomeLoadError):
            ingest_genome(tmp_path / "nonexistent.json")

    def test_signing_key_env_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """THALOS_NEXUS_SIGNING_KEY env var affects signature but not hash."""
        from thalos_nexus.nucleus import ingest_genome

        genome_path = _sample_genome(tmp_path)
        monkeypatch.setenv("THALOS_NEXUS_SIGNING_KEY", "custom-key-123")
        b_custom = ingest_genome(genome_path)
        monkeypatch.delenv("THALOS_NEXUS_SIGNING_KEY", raising=False)
        b_dev = ingest_genome(genome_path)
        assert b_custom.genome_hash == b_dev.genome_hash
        assert b_custom.signature != b_dev.signature

    def test_bundle_to_dict(self, tmp_path: Path) -> None:
        """to_dict returns expected keys."""
        from thalos_nexus.nucleus import ingest_genome

        bundle = ingest_genome(_sample_genome(tmp_path))
        d = bundle.to_dict()
        for key in ("genome_id", "genome_hash", "signature", "intent", "policy", "fitness", "lineages", "created_at"):
            assert key in d


# ---------------------------------------------------------------------------
# spine tests
# ---------------------------------------------------------------------------


class TestDeterminismSpine:
    """Tests for thalos_nexus.spine.DeterminismSpine."""

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        """DeterminismSpine creates the output directory."""
        from thalos_nexus.spine import DeterminismSpine

        out = tmp_path / "nexus_out"
        DeterminismSpine(out)
        assert out.is_dir()

    def test_write_repro_manifest(self, tmp_path: Path) -> None:
        """write_repro_manifest creates a valid JSON file."""
        from thalos_nexus.spine import DeterminismSpine

        spine = DeterminismSpine(tmp_path)
        path = spine.write_repro_manifest(
            seed=42,
            config_hash="abc123",
            version="3.0.0",
            genome_hash="deadbeef",
        )
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["seed"] == 42
        assert data["config_hash"] == "abc123"
        assert data["genome_hash"] == "deadbeef"

    def test_emit_event_creates_log_file(self, tmp_path: Path) -> None:
        """emit_event appends to event_log.jsonl."""
        from thalos_nexus.spine import DeterminismSpine

        spine = DeterminismSpine(tmp_path)
        spine.emit_event("test.event", {"key": "value"})
        log_path = tmp_path / "event_log.jsonl"
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["event_type"] == "test.event"

    def test_event_log_hash_chain(self, tmp_path: Path) -> None:
        """Each event's prev_hash matches the previous event's event_hash."""
        from thalos_nexus.spine import DeterminismSpine

        spine = DeterminismSpine(tmp_path)
        for i in range(3):
            spine.emit_event("ev", {"i": i})

        log_path = tmp_path / "event_log.jsonl"
        events = [json.loads(line) for line in log_path.read_text().strip().splitlines()]
        assert events[0]["prev_hash"] == ""
        assert events[1]["prev_hash"] == events[0]["event_hash"]
        assert events[2]["prev_hash"] == events[1]["event_hash"]

    def test_write_gate_results(self, tmp_path: Path) -> None:
        """write_gate_results creates a valid JSON file."""
        from thalos_nexus.spine import DeterminismSpine

        spine = DeterminismSpine(tmp_path)
        results = {
            "all_passed": True,
            "total_duration_seconds": 1.5,
            "gates": [],
        }
        path = spine.write_gate_results(results)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["all_passed"] is True

    def test_write_artifacts(self, tmp_path: Path) -> None:
        """write_artifacts creates a valid JSON file."""
        from thalos_nexus.spine import DeterminismSpine

        spine = DeterminismSpine(tmp_path)
        path = spine.write_artifacts([{"name": "foo.json", "path": "/tmp/foo.json"}])
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data["artifacts"]) == 1

    def test_all_output_paths(self, tmp_path: Path) -> None:
        """all_output_paths returns paths for files that exist."""
        from thalos_nexus.spine import DeterminismSpine

        spine = DeterminismSpine(tmp_path)
        spine.write_repro_manifest(seed=1, config_hash="x", version="3.0.0", genome_hash="y")
        spine.emit_event("test", {})
        paths = spine.all_output_paths()
        names = {p.name for p in paths}
        assert "repro_manifest.json" in names
        assert "event_log.jsonl" in names


# ---------------------------------------------------------------------------
# lysosome tests
# ---------------------------------------------------------------------------


class TestGateRunner:
    """Tests for thalos_nexus.lysosome.GateRunner."""

    def test_run_passing_gate(self, tmp_path: Path) -> None:
        """A gate running a passing command returns passed=True."""
        from thalos_nexus.gates import GateSpec
        from thalos_nexus.lysosome import GateRunner

        gate = GateSpec(
            name="echo-test",
            commands=[[sys.executable, "-c", "print('hello'); import sys; sys.exit(0)"]],
            fatal=False,
            description="Echo test",
        )
        runner = GateRunner(gates=[gate])
        results = runner.run()
        assert results.all_passed is True
        assert len(results.results) == 1
        assert results.results[0].passed is True
        assert results.results[0].exit_code == 0

    def test_run_failing_gate(self) -> None:
        """A gate running a failing command returns passed=False."""
        from thalos_nexus.gates import GateSpec
        from thalos_nexus.lysosome import GateRunner

        gate = GateSpec(
            name="fail-test",
            commands=[[sys.executable, "-c", "import sys; sys.exit(1)"]],
            fatal=False,
            description="Fail test",
        )
        runner = GateRunner(gates=[gate])
        results = runner.run()
        assert results.all_passed is False
        assert results.results[0].passed is False
        assert results.results[0].exit_code == 1

    def test_fatal_gate_stops_execution(self) -> None:
        """A fatal failing gate stops execution of subsequent gates."""
        from thalos_nexus.gates import GateSpec
        from thalos_nexus.lysosome import GateRunner

        gate_fatal = GateSpec(
            name="fatal-gate",
            commands=[[sys.executable, "-c", "import sys; sys.exit(1)"]],
            fatal=True,
            description="Fatal gate",
        )
        gate_after = GateSpec(
            name="should-not-run",
            commands=[[sys.executable, "-c", "print('should not appear')"]],
            fatal=False,
            description="Should not run",
        )
        runner = GateRunner(gates=[gate_fatal, gate_after])
        results = runner.run()
        assert results.all_passed is False
        assert len(results.results) == 1  # second gate never runs

    def test_gate_result_to_dict(self) -> None:
        """GateResult.to_dict produces expected keys."""
        from thalos_nexus.lysosome import GateResult

        r = GateResult(
            gate_name="x",
            passed=True,
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_seconds=0.1,
            fatal=False,
        )
        d = r.to_dict()
        assert d["name"] == "x"
        assert d["passed"] is True


# ---------------------------------------------------------------------------
# mitochondria tests
# ---------------------------------------------------------------------------


class TestBudgetGovernor:
    """Tests for thalos_nexus.mitochondria.BudgetGovernor."""

    def test_initial_state(self) -> None:
        """Before start(), elapsed is 0 and remaining equals total."""
        from thalos_nexus.mitochondria import BudgetGovernor

        gov = BudgetGovernor(total_budget_seconds=60.0)
        assert gov.elapsed_seconds() == 0.0
        assert gov.remaining_seconds() == 60.0
        assert gov.is_over_budget() is False

    def test_start_and_elapsed(self) -> None:
        """After start(), elapsed time is positive."""
        from thalos_nexus.mitochondria import BudgetGovernor

        gov = BudgetGovernor(total_budget_seconds=60.0)
        gov.start()
        time.sleep(0.01)
        assert gov.elapsed_seconds() > 0.0

    def test_is_over_budget(self) -> None:
        """Tiny budget is exceeded after sleeping."""
        from thalos_nexus.mitochondria import BudgetGovernor

        gov = BudgetGovernor(total_budget_seconds=0.01)
        gov.start()
        time.sleep(0.05)
        assert gov.is_over_budget() is True

    def test_allocate_gate_budget(self) -> None:
        """allocate_gate_budget returns a positive number."""
        from thalos_nexus.mitochondria import BudgetGovernor

        gov = BudgetGovernor(total_budget_seconds=60.0)
        gov.start()
        alloc = gov.allocate_gate_budget("test-gate")
        assert alloc > 0.0

    def test_invalid_budget_raises(self) -> None:
        """Non-positive budget raises ValueError."""
        from thalos_nexus.mitochondria import BudgetGovernor

        with pytest.raises(ValueError, match="positive"):
            BudgetGovernor(total_budget_seconds=-1.0)


# ---------------------------------------------------------------------------
# cytoplasm tests
# ---------------------------------------------------------------------------


class TestToolRegistry:
    """Tests for thalos_nexus.cytoplasm.ToolRegistry."""

    def test_register_and_get(self) -> None:
        """Registered tools can be retrieved."""
        from thalos_nexus.cytoplasm import ToolEnvelope, ToolRegistry

        reg = ToolRegistry()
        tool = ToolEnvelope(name="ruff", command="ruff", default_args=["check"])
        reg.register(tool)
        assert reg.get("ruff") is tool

    def test_get_missing_raises(self) -> None:
        """Getting an unregistered tool raises ToolNotFoundError."""
        from thalos_nexus.cytoplasm import ToolNotFoundError, ToolRegistry

        reg = ToolRegistry()
        with pytest.raises(ToolNotFoundError):
            reg.get("nonexistent")

    def test_execute_python_version(self) -> None:
        """execute() runs a real command and returns CompletedProcess."""
        from thalos_nexus.cytoplasm import ToolEnvelope, ToolRegistry

        reg = ToolRegistry()
        reg.register(
            ToolEnvelope(
                name="py",
                command=sys.executable,
                default_args=["--version"],
            )
        )
        result = reg.execute("py")
        assert result.returncode == 0

    def test_list_tools(self) -> None:
        """list_tools returns sorted tool names."""
        from thalos_nexus.cytoplasm import ToolEnvelope, ToolRegistry

        reg = ToolRegistry()
        reg.register(ToolEnvelope(name="z-tool", command="z"))
        reg.register(ToolEnvelope(name="a-tool", command="a"))
        assert reg.list_tools() == ["a-tool", "z-tool"]

    def test_overwrite_registration(self) -> None:
        """Re-registering a tool name overwrites the old entry."""
        from thalos_nexus.cytoplasm import ToolEnvelope, ToolRegistry

        reg = ToolRegistry()
        reg.register(ToolEnvelope(name="t", command="old"))
        reg.register(ToolEnvelope(name="t", command="new"))
        assert reg.get("t").command == "new"


# ---------------------------------------------------------------------------
# er tests
# ---------------------------------------------------------------------------


class TestArtifactFolder:
    """Tests for thalos_nexus.er.ArtifactFolder."""

    def test_fold_creates_zip(self, tmp_path: Path) -> None:
        """fold() creates a zip archive containing the specified files."""
        from thalos_nexus.er import ArtifactFolder

        f = tmp_path / "sample.txt"
        f.write_text("hello")
        folder = ArtifactFolder()
        zip_path = folder.fold(files=[str(f)], output_path=str(tmp_path / "out.zip"))
        assert Path(zip_path).exists()
        with zipfile.ZipFile(zip_path) as zf:
            assert "sample.txt" in zf.namelist()

    def test_fold_missing_file_recorded(self, tmp_path: Path) -> None:
        """fold() records missing files in _missing.txt."""
        from thalos_nexus.er import ArtifactFolder

        folder = ArtifactFolder()
        zip_path = folder.fold(
            files=[str(tmp_path / "does_not_exist.json")],
            output_path=str(tmp_path / "bundle.zip"),
        )
        with zipfile.ZipFile(zip_path) as zf:
            assert "_missing.txt" in zf.namelist()

    def test_generate_sbom(self, tmp_path: Path) -> None:
        """generate_sbom() writes a JSON file with the correct structure."""
        from thalos_nexus.er import ArtifactFolder

        folder = ArtifactFolder()
        sbom_path = folder.generate_sbom(
            packages=["requests==2.31.0:Apache-2.0", "pytest==8.0.0:MIT"],
            output_path=str(tmp_path / "sbom.json"),
        )
        data = json.loads(Path(sbom_path).read_text())
        assert data["schema_version"] == "1.0"
        assert len(data["components"]) == 2
        names = {c["name"] for c in data["components"]}
        assert "requests" in names

    def test_sbom_entry_no_version(self, tmp_path: Path) -> None:
        """generate_sbom handles spec without version."""
        from thalos_nexus.er import ArtifactFolder

        folder = ArtifactFolder()
        sbom_path = folder.generate_sbom(
            packages=["some-package"],
            output_path=str(tmp_path / "sbom2.json"),
        )
        data = json.loads(Path(sbom_path).read_text())
        assert data["components"][0]["version"] == "UNKNOWN"


# ---------------------------------------------------------------------------
# gates tests
# ---------------------------------------------------------------------------


class TestGates:
    """Tests for thalos_nexus.gates."""

    def test_standard_gates_count(self) -> None:
        """STANDARD_GATES has exactly 8 gates."""
        from thalos_nexus.gates import STANDARD_GATES

        assert len(STANDARD_GATES) == 8

    def test_gate_spec_fields(self) -> None:
        """All GateSpec objects have non-empty names and descriptions."""
        from thalos_nexus.gates import STANDARD_GATES

        for gate in STANDARD_GATES:
            assert gate.name
            assert gate.description
            assert isinstance(gate.commands, list)
            assert len(gate.commands) >= 1

    def test_no_placeholder_gate_is_fatal(self) -> None:
        """The no-placeholder gate is marked as fatal."""
        from thalos_nexus.gates import STANDARD_GATES

        gate = next(g for g in STANDARD_GATES if g.name == "no-placeholder")
        assert gate.fatal is True

    def test_deterministic_replay_gate_is_fatal(self) -> None:
        """The deterministic-replay gate is marked as fatal."""
        from thalos_nexus.gates import STANDARD_GATES

        gate = next(g for g in STANDARD_GATES if g.name == "deterministic-replay")
        assert gate.fatal is True


# ---------------------------------------------------------------------------
# membrane tests
# ---------------------------------------------------------------------------


class TestMembraneGateway:
    """Tests for thalos_nexus.membrane.MembraneGateway."""

    def test_dry_run_context_manager(self) -> None:
        """MembraneGateway dry-run succeeds without invoking netsh."""
        from thalos_nexus.membrane import MembraneGateway

        with MembraneGateway(allowed_hosts=["example.com"], dry_run=True) as gw:
            assert gw.rule_name.startswith("ThalosPrime-NEXUS-")

    def test_rule_name_unique(self) -> None:
        """Each MembraneGateway instance gets a unique rule name."""
        from thalos_nexus.membrane import MembraneGateway

        gw1 = MembraneGateway(dry_run=True)
        gw2 = MembraneGateway(dry_run=True)
        assert gw1.rule_name != gw2.rule_name

    def test_exit_called_on_exception(self) -> None:
        """__exit__ is called even when an exception is raised inside the block."""
        from thalos_nexus.membrane import MembraneGateway

        with pytest.raises(RuntimeError, match="test error"):
            with MembraneGateway(dry_run=True):
                raise RuntimeError("test error")


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for thalos_nexus.cli."""

    def test_help_exits_zero(self) -> None:
        """--help exits with code 0."""
        from thalos_nexus.cli import build_parser

        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        assert exc_info.value.code == 0

    def test_version_exits_zero(self) -> None:
        """--version exits with code 0."""
        from thalos_nexus.cli import build_parser

        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0

    def test_ingest_genome_command(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """ingest-genome command prints a JSON bundle to stdout."""
        from thalos_nexus.cli import main

        genome_path = _sample_genome(tmp_path)
        rc = main(["ingest-genome", str(genome_path)])
        captured = capsys.readouterr()
        assert rc == 0
        data = json.loads(captured.out)
        assert data["genome_id"] == "test-genome-001"

    def test_ingest_genome_bad_file(self, tmp_path: Path) -> None:
        """ingest-genome with a bad file returns exit code 1."""
        from thalos_nexus.cli import main

        rc = main(["ingest-genome", str(tmp_path / "nonexistent.json")])
        assert rc == 1

    def test_traits_command(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """traits command prints genome traits as JSON."""
        from thalos_nexus.cli import main

        genome_path = _sample_genome(tmp_path)
        rc = main(["traits", "--genome", str(genome_path)])
        captured = capsys.readouterr()
        assert rc == 0
        data = json.loads(captured.out)
        assert data["genome_id"] == "test-genome-001"

    def test_traits_no_genome_returns_error(self) -> None:
        """traits without --genome returns exit code 1."""
        from thalos_nexus.cli import main

        rc = main(["traits"])
        assert rc == 1

    def test_replay_missing_manifest(self, tmp_path: Path) -> None:
        """replay with a missing manifest returns exit code 1."""
        from thalos_nexus.cli import main

        rc = main(["replay", "--manifest", str(tmp_path / "missing.json")])
        assert rc == 1

    def test_immunome_no_results(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """immunome without gate_results.json prints a friendly message."""
        from thalos_nexus.cli import main

        rc = main(["immunome", "--output-dir", str(tmp_path)])
        captured = capsys.readouterr()
        assert rc == 0
        assert "Run 'evolve' first" in captured.out

    def test_package_exports(self) -> None:
        """Key symbols are importable from thalos_nexus top-level."""
        import thalos_nexus

        assert hasattr(thalos_nexus, "__version__")
        assert hasattr(thalos_nexus, "GenomeBundle")
        assert hasattr(thalos_nexus, "DeterminismSpine")
