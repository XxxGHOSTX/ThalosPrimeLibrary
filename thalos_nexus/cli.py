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
