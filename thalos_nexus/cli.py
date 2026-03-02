"""Thalos Prime NEXUS Core v1 — Command-Line Interface.

Entry point for the three NEXUS commands:

* ``ingest-genome`` — hash a genome file, generate SBOM, sign and bundle it.
* ``evolve`` — run all hard gates for a genome/task combination, write artifacts.
* ``replay`` — verify a repro_manifest and its artifacts.

Run as ``python -m thalos_nexus.cli --help``.

Control Plane boundary: orchestration of nucleus, attest, and tools subsystems
only.  No computational logic belongs here.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool) -> None:
    """Configure root logger level and format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _compute_file_sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of *path*."""
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def cmd_ingest_genome(args: argparse.Namespace) -> int:
    """Implement the ``ingest-genome`` sub-command.

    Reads the genome file at ``args.path``, computes its SHA-256 hash, creates
    a zip bundle (``trait_bundle.zip``), generates a SBOM, signs the manifest,
    and writes everything to ``args.out_dir/{genome_hash}/``.

    Args:
        args: Parsed argument namespace.

    Returns:
        Exit code (0 = success, non-zero = failure).

    """
    from thalos_nexus.attest.sbom import SbomGenerator
    from thalos_nexus.attest.signing import load_or_generate_keypair, sign_manifest
    from thalos_nexus.nucleus.artifacts import ArtifactStore
    from thalos_nexus.nucleus.determinism import (
        compute_config_hash,
        compute_run_id,
    )

    genome_path = Path(args.path)
    if not genome_path.exists():
        print(f"ERROR: genome file not found: {genome_path}", file=sys.stderr)
        return 1

    genome_hash = _compute_file_sha256(genome_path)
    key_dir = Path(args.key_dir)
    out_dir = Path(args.out_dir) / genome_hash
    out_dir.mkdir(parents=True, exist_ok=True)

    store = ArtifactStore(out_dir)

    zip_path = out_dir / "trait_bundle.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(genome_path, genome_path.name)
    bundle_sha = _compute_file_sha256(zip_path)

    sbom_gen = SbomGenerator()
    sbom_path = out_dir / "sbom.json"
    sbom_sha = sbom_gen.generate(genome_path.parent, sbom_path)

    config: dict[str, Any] = {"genome_hash": genome_hash}
    config_hash = compute_config_hash(config)
    run_id = compute_run_id(0, "ingest", genome_hash, config_hash)

    from thalos_nexus.nucleus.determinism import EventLogWriter

    log_path = out_dir / "event_log.jsonl"
    writer = EventLogWriter(log_path)
    writer.append("ingest_genome_start", {"genome_hash": genome_hash, "run_id": run_id})
    writer.append("sbom_generated", {"sha256": sbom_sha})
    writer.append("bundle_created", {"sha256": bundle_sha})
    writer.append("ingest_genome_complete", {"genome_hash": genome_hash})
    log_sha = _compute_file_sha256(log_path)

    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "genome_hash": genome_hash,
        "task": "ingest",
        "seed": 0,
        "config_hash": config_hash,
        "timestamp": datetime.now(UTC).isoformat(),
        "artifacts": {
            "gate_results": store.make_artifact_ref(
                "gate_results",
                out_dir / "gate_results.json",
                hashlib.sha256(b"{}").hexdigest(),
            ),
            "event_log": store.make_artifact_ref("event_log", log_path, log_sha),
            "sbom": store.make_artifact_ref("sbom", sbom_path, sbom_sha),
            "trait_bundle": store.make_artifact_ref("trait_bundle", zip_path, bundle_sha),
        },
    }

    empty_gate_results: dict[str, Any] = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "overall_passed": True,
        "gates": [
            {
                "name": "ingest",
                "passed": True,
                "duration_seconds": 0.0,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "error": None,
            }
        ],
    }
    gate_path, gate_sha = store.write_json("gate_results.json", empty_gate_results)
    manifest["artifacts"]["gate_results"] = store.make_artifact_ref(
        "gate_results", gate_path, gate_sha
    )

    kp = load_or_generate_keypair(key_dir)
    signed = sign_manifest(manifest, kp)
    store.write_json("repro_manifest.json", signed)

    print(genome_hash)
    return 0


def cmd_evolve(args: argparse.Namespace) -> int:
    """Implement the ``evolve`` sub-command.

    Creates a run directory, executes all hard gates via :class:`GateRunner`,
    writes ``gate_results.json``, ``event_log.jsonl``, and a signed
    ``repro_manifest.json``.

    Args:
        args: Parsed argument namespace.

    Returns:
        Exit code (0 = success, non-zero = failure).

    """
    from thalos_nexus.attest.signing import load_or_generate_keypair, sign_manifest
    from thalos_nexus.nucleus.artifacts import ArtifactStore
    from thalos_nexus.nucleus.determinism import (
        EventLogWriter,
        compute_config_hash,
        compute_run_id,
    )
    from thalos_nexus.tools.gates import GateContext, GateRunner

    genome_hash: str = args.genome
    task: str = args.task
    seed: int = args.seed
    key_dir = Path(args.key_dir)
    target_dir = Path(args.target_dir)
    python_exec: str = args.python

    config: dict[str, Any] = {"genome_hash": genome_hash, "task": task, "seed": seed}
    config_hash = compute_config_hash(config)
    run_id = compute_run_id(seed, task, genome_hash, config_hash)

    run_dir = Path(args.run_dir) if args.run_dir else Path("nexus_runs") / run_id

    run_dir.mkdir(parents=True, exist_ok=True)
    store = ArtifactStore(run_dir)

    log_path = run_dir / "event_log.jsonl"
    writer = EventLogWriter(log_path)
    writer.append("evolve_start", {"run_id": run_id, "genome_hash": genome_hash, "task": task})

    if sys.platform != "win32":
        print(
            "WARNING: running on non-Windows platform; "
            "IsolationAdapter is unavailable; gates run directly.",
            file=sys.stderr,
        )

    ctx = GateContext(
        run_id=run_id,
        target_dir=target_dir,
        workspace_dir=run_dir / "workspace",
        python_executable=python_exec,
        timeout_seconds=300.0,
    )
    (run_dir / "workspace").mkdir(exist_ok=True)

    runner = GateRunner(ctx)
    results = runner.run_all()

    for r in results:
        writer.append(
            "gate_result",
            {
                "name": r.name,
                "passed": r.passed,
                "exit_code": r.exit_code,
                "duration_seconds": r.duration_seconds,
            },
        )

    overall_passed = all(r.passed for r in results)
    writer.append("evolve_complete", {"overall_passed": overall_passed, "run_id": run_id})

    now = datetime.now(UTC).isoformat()
    gate_data: dict[str, Any] = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "timestamp": now,
        "overall_passed": overall_passed,
        "gates": [
            {
                "name": r.name,
                "passed": r.passed,
                "duration_seconds": r.duration_seconds,
                "exit_code": r.exit_code,
                "stdout": r.stdout,
                "stderr": r.stderr,
                "error": r.error,
            }
            for r in results
        ],
    }
    gate_path, gate_sha = store.write_json("gate_results.json", gate_data)
    log_sha = _compute_file_sha256(log_path)

    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "genome_hash": genome_hash,
        "task": task,
        "seed": seed,
        "config_hash": config_hash,
        "timestamp": now,
        "artifacts": {
            "gate_results": store.make_artifact_ref("gate_results", gate_path, gate_sha),
            "event_log": store.make_artifact_ref("event_log", log_path, log_sha),
        },
    }

    kp = load_or_generate_keypair(key_dir)
    signed = sign_manifest(manifest, kp)
    store.write_json("repro_manifest.json", signed)

    status = "PASS" if overall_passed else "FAIL"
    print(f"evolve {status}: run_id={run_id} dir={run_dir}")
    return 0 if overall_passed else 1


def cmd_replay(args: argparse.Namespace) -> int:
    """Implement the ``replay`` sub-command.

    Loads the repro_manifest, verifies artifact integrity and event-log chain,
    and optionally verifies the ed25519 signature.

    Args:
        args: Parsed argument namespace.

    Returns:
        Exit code (0 = PASS, 1 = FAIL).

    """
    from thalos_nexus.nucleus.replay import ReplayVerifier

    manifest_path = Path(args.repro_manifest)
    artifacts_dir = manifest_path.parent

    verifier = ReplayVerifier()
    errors = verifier.verify_manifest(manifest_path, artifacts_dir)

    if args.key:
        sig_errors = verifier.verify_signature(manifest_path, args.key)
        errors.extend(sig_errors)

    if errors:
        print("FAIL")
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1

    print("PASS")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="thalos_nexus",
        description="Thalos Prime NEXUS Core v1 — deterministic evolution pipeline",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    ig = sub.add_parser("ingest-genome", help="Ingest a genome file and create a signed bundle")
    ig.add_argument("--path", required=True, metavar="PATH", help="Path to genome file")
    ig.add_argument(
        "--key-dir",
        default=str(Path.home() / ".thalos_nexus" / "keys"),
        metavar="KEY_DIR",
        help="Directory for ed25519 key PEM files (default: ~/.thalos_nexus/keys)",
    )
    ig.add_argument(
        "--out-dir",
        default="./nexus_runs",
        metavar="OUT_DIR",
        help="Output base directory (default: ./nexus_runs)",
    )

    ev = sub.add_parser("evolve", help="Run all hard gates for a genome/task combination")
    ev.add_argument("--genome", required=True, metavar="GENOME_HASH", help="Genome SHA-256 hash")
    ev.add_argument("--task", required=True, metavar="TASK", help="Task descriptor string")
    ev.add_argument("--seed", type=int, default=0, metavar="SEED", help="Random seed (default: 0)")
    ev.add_argument("--run-dir", default="", metavar="RUN_DIR", help="Override run output dir")
    ev.add_argument(
        "--key-dir",
        default=str(Path.home() / ".thalos_nexus" / "keys"),
        metavar="KEY_DIR",
        help="Directory for ed25519 key PEM files",
    )
    ev.add_argument(
        "--target-dir",
        default=".",
        metavar="TARGET_DIR",
        help="Directory to run gates on (default: current dir)",
    )
    ev.add_argument(
        "--python",
        default=sys.executable,
        metavar="PYTHON",
        help="Python interpreter for gate subprocesses",
    )

    rp = sub.add_parser("replay", help="Verify a repro_manifest and its artifacts")
    rp.add_argument(
        "--repro-manifest",
        required=True,
        metavar="PATH",
        help="Path to repro_manifest.json",
    )
    rp.add_argument(
        "--key",
        default="",
        metavar="PUBLIC_KEY_HEX",
        help="Hex-encoded ed25519 public key for signature verification",
    )

    return parser


def main() -> None:
    """CLI entry point — parse arguments and dispatch to sub-command handler."""
    parser = build_parser()
    args = parser.parse_args()
    _setup_logging(getattr(args, "verbose", False))

    dispatch: dict[str, Any] = {
        "ingest-genome": cmd_ingest_genome,
        "evolve": cmd_evolve,
        "replay": cmd_replay,
    }
    handler = dispatch[args.command]
    sys.exit(handler(args))


if __name__ == "__main__":
    main()
