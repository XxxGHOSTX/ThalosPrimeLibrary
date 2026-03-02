"""Deterministic tests for the Thalos Prime NEXUS Core v1 vertical slice.

All tests are deterministic: no randomness without explicit seeds, no network
access, no reliance on wall-clock time for correctness.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

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
