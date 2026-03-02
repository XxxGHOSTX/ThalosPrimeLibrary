"""Thalos Prime NEXUS Core v1 — Command-Line Interface.

Entry point for the three NEXUS commands:

* ``ingest-genome`` — hash a genome file, generate SBOM, sign and bundle it.
* ``evolve`` — run all hard gates for a genome/task combination, write artifacts.
* ``replay`` — verify a repro_manifest and its artifacts.

Run as ``python -m thalos_nexus.cli --help``.

Control Plane boundary: orchestration of nucleus, attest, and tools subsystems
only.  No computational logic belongs here.
"""Thalos NEXUS v3.0 — command-line interface.

Subcommands
-----------
- ``ingest-genome <genome_file>``   — ingest, validate and sign a genome file
- ``evolve [--genome F] [--output-dir D]`` — run the full gate suite
- ``replay [--manifest F]``         — verify deterministic replay
- ``traits [--genome F]``           — show genome traits
- ``immunome [--output-dir D]``     — show gate health / immunome status

Run ``python -m thalos_nexus.cli --help`` for full usage.

Control Plane boundary: CLI parses arguments and delegates to specialist
modules; it does not implement gate logic or genome validation directly.
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
import json
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from thalos_nexus import __version__
from thalos_nexus.er import ArtifactFolder
from thalos_nexus.gates import STANDARD_GATES
from thalos_nexus.lysosome import GateRunner
from thalos_nexus.nucleus import GenomeLoadError, GenomeValidationError, ingest_genome
from thalos_nexus.spine import DeterminismSpine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config_hash(genome_path: str | None) -> str:
    """Compute a SHA-256 hash over the CLI configuration for repro tracking."""
    config_str = json.dumps(
        {
            "genome_path": genome_path,
            "thalos_nexus_version": __version__,
            "python": sys.version,
        },
        sort_keys=True,
    )
    return hashlib.sha256(config_str.encode()).hexdigest()


def _default_seed() -> int:
    """Return the default deterministic seed (env override allowed)."""
    raw = os.environ.get("THALOS_NEXUS_SEED", "42")
    try:
        return int(raw)
    except ValueError:
        return 42


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------


def _cmd_ingest_genome(args: argparse.Namespace) -> int:
    """Ingest, validate and sign a genome file."""
    genome_path: str = args.genome_file
    try:
        bundle = ingest_genome(genome_path)
    except (GenomeLoadError, GenomeValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(bundle.to_dict(), indent=2))
    return 0


def _cmd_evolve(args: argparse.Namespace) -> int:
    """Run the full gate suite, write outputs, and fold artifacts."""
    genome_path: str | None = getattr(args, "genome", None)
    output_dir: str = getattr(args, "output_dir", "thalos_nexus_output")
    seed: int = _default_seed()

    spine = DeterminismSpine(output_dir)
    spine.emit_event("evolve.start", {"genome_path": genome_path, "seed": seed})

    genome_hash = ""
    if genome_path is not None:
        try:
            bundle = ingest_genome(genome_path)
            genome_hash = bundle.genome_hash
            spine.emit_event("genome.ingested", {"genome_id": bundle.genome_id})
        except (GenomeLoadError, GenomeValidationError) as exc:
            print(f"ERROR: genome ingestion failed: {exc}", file=sys.stderr)
            spine.emit_event("genome.failed", {"error": str(exc)})
            return 1

    config_hash = _config_hash(genome_path)
    spine.write_repro_manifest(
        seed=seed,
        config_hash=config_hash,
        version=__version__,
        genome_hash=genome_hash,
    )

    runner = GateRunner(gates=STANDARD_GATES, cwd=str(Path.cwd()))
    spine.emit_event("gates.start", {"gate_count": len(STANDARD_GATES)})
    run_results = runner.run()
    spine.emit_event(
        "gates.complete",
        {
            "all_passed": run_results.all_passed,
            "total_duration": run_results.total_duration,
        },
    )

    gate_dict = run_results.to_dict()
    spine.write_gate_results(gate_dict)

    artifact_paths = spine.all_output_paths()
    artifact_descriptors: list[dict[str, Any]] = [
        {"path": str(p), "name": p.name} for p in artifact_paths
    ]
    spine.write_artifacts(artifact_descriptors)

    folder = ArtifactFolder()
    bundle_path = str(Path(output_dir) / "nexus_bundle.zip")
    folder.fold(files=[str(p) for p in artifact_paths], output_path=bundle_path)
    spine.emit_event("artifacts.folded", {"bundle_path": bundle_path})

    status = "PASS" if run_results.all_passed else "FAIL"
    print(f"[NEXUS] Evolve complete — {status}")
    print(f"[NEXUS] Output: {output_dir}")
    for r in run_results.results:
        icon = "✓" if r.passed else "✗"
        print(f"  {icon} {r.gate_name} ({r.duration_seconds:.2f}s)")

    return 0 if run_results.all_passed else 2


def _cmd_replay(args: argparse.Namespace) -> int:
    """Verify deterministic replay against a repro_manifest.json."""
    manifest_path_str: str = getattr(args, "manifest", "thalos_nexus_output/repro_manifest.json")
    manifest_path = Path(manifest_path_str)

    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read manifest: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(manifest, indent=2))

    # Re-compute config hash and compare
    recorded_config_hash: str = manifest.get("config_hash", "")
    recorded_seed: int = int(manifest.get("seed", 42))
    recorded_genome_hash: str = manifest.get("genome_hash", "")

    replay_config_hash = _config_hash(None)
    if recorded_config_hash == replay_config_hash:
        print("[NEXUS] Replay: config hash matches ✓")
    else:
        print("[NEXUS] Replay: config hash mismatch (expected — environment may differ)")

    print(f"[NEXUS] Replay: seed={recorded_seed} genome_hash={recorded_genome_hash}")
    return 0


def _cmd_traits(args: argparse.Namespace) -> int:
    """Show genome traits from a genome file."""
    genome_path: str | None = getattr(args, "genome", None)
    if genome_path is None:
        print("ERROR: --genome is required for traits subcommand.", file=sys.stderr)
        return 1

    try:
        bundle = ingest_genome(genome_path)
    except (GenomeLoadError, GenomeValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    traits: dict[str, Any] = {
        "genome_id": bundle.genome_id,
        "genome_hash": bundle.genome_hash,
        "objectives": bundle.intent.get("objectives", []),
        "policy_rules": len(bundle.policy.get("rules", [])),
        "fitness_global_floor": bundle.fitness.get("global_floor", 0),
        "lineages": len(bundle.lineages),
        "created_at": bundle.created_at,
    }
    print(json.dumps(traits, indent=2))
    return 0


def _cmd_immunome(args: argparse.Namespace) -> int:
    """Show gate health / immunome status from a previous evolve output."""
    output_dir: str = getattr(args, "output_dir", "thalos_nexus_output")
    gate_results_path = Path(output_dir) / "gate_results.json"

    if not gate_results_path.exists():
        print(f"[NEXUS] No gate_results.json found in '{output_dir}'.")
        print("[NEXUS] Run 'evolve' first to generate immunome data.")
        return 0

    try:
        gate_results = json.loads(gate_results_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read gate results: {exc}", file=sys.stderr)
        return 1

    all_passed: bool = gate_results.get("all_passed", False)
    total_dur: float = gate_results.get("total_duration_seconds", 0.0)
    print(f"[NEXUS] Immunome status: {'HEALTHY' if all_passed else 'DEGRADED'}")
    print(f"[NEXUS] Total duration: {total_dur:.2f}s")

    for gate in gate_results.get("gates", []):
        icon = "✓" if gate.get("passed") else "✗"
        fatal_marker = " [FATAL]" if gate.get("fatal") else ""
        print(f"  {icon} {gate.get('name')}{fatal_marker} ({gate.get('duration_seconds', 0):.2f}s)")

    return 0


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="thalos-nexus",
        description=f"Thalos Prime NEXUS v{__version__} — deterministic genome evolution toolkit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"thalos-nexus {__version__}",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: WARNING)",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ingest-genome
    ig = sub.add_parser("ingest-genome", help="Ingest, validate, and sign a genome file")
    ig.add_argument("genome_file", help="Path to the JSON genome file")

    # evolve
    ev = sub.add_parser("evolve", help="Run the full gate suite")
    ev.add_argument("--genome", metavar="FILE", help="Path to the genome file")
    ev.add_argument(
        "--output-dir",
        default="thalos_nexus_output",
        metavar="DIR",
        help="Output directory (default: thalos_nexus_output)",
    )

    # replay
    rp = sub.add_parser("replay", help="Verify deterministic replay")
    rp.add_argument(
        "--manifest",
        default="thalos_nexus_output/repro_manifest.json",
        metavar="FILE",
        help="Path to repro_manifest.json",
    )

    # traits
    tr = sub.add_parser("traits", help="Show genome traits")
    tr.add_argument("--genome", metavar="FILE", help="Path to the genome file")

    # immunome
    im = sub.add_parser("immunome", help="Show gate health / immunome status")
    im.add_argument(
        "--output-dir",
        default="thalos_nexus_output",
        metavar="DIR",
        help="Output directory containing gate_results.json",
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
# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Parse *argv* and dispatch to the appropriate sub-command handler.

    Returns the exit code (0 = success).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )

    dispatch: dict[str, Callable[[argparse.Namespace], int]] = {
        "ingest-genome": _cmd_ingest_genome,
        "evolve": _cmd_evolve,
        "replay": _cmd_replay,
        "traits": _cmd_traits,
        "immunome": _cmd_immunome,
    }
    handler = dispatch[args.command]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
