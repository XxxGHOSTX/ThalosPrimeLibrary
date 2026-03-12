"""Thalos infra-synthesis CLI.

Provides three sub-commands:

* ``thalos build``  — Generate provider artifacts from a schema.
* ``thalos verify`` — Validate a schema and evaluate policies.
* ``thalos deploy`` — Run the selected release strategy.

Entry point: ``thalos`` → ``thalos_prime.infra_synthesis.cli.main:main``.
"""

from __future__ import annotations

import argparse
import logging
import sys

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=level,
    )


def _cmd_build(args: argparse.Namespace) -> int:
    """Execute the ``build`` sub-command.

    Loads the schema, validates it, generates all provider artifacts, and
    writes ``artifact_manifest.json`` to the output directory.

    Args:
        args: Parsed CLI namespace with ``schema`` and ``out`` attributes.

    Returns:
        Exit code (0 on success, 1 on error).

    """
    from thalos_prime.infra_synthesis.engine import InfraSynthesisEngine

    engine = InfraSynthesisEngine()
    try:
        result = engine.generate(schema_path=args.schema, out_dir=args.out)
    except (ValueError, OSError) as exc:
        print(f"ERROR: build failed — {exc}", flush=True)
        logger.exception("build failed")
        return 1

    print(f"Build complete — {len(result.artifacts)} artifact(s) in '{result.out_dir}'")
    for rel, digest in sorted(result.manifest.items()):
        print(f"  {rel}  {digest[:12]}…")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    """Execute the ``verify`` sub-command.

    Loads and validates the schema, then evaluates all registered policy rules.

    Args:
        args: Parsed CLI namespace with ``schema`` attribute.

    Returns:
        Exit code (0 when valid + all policies pass, 1 otherwise).

    """
    from thalos_prime.infra_synthesis.policy.engine import PolicyEngine
    from thalos_prime.infra_synthesis.schema_loader import SchemaLoader
    from thalos_prime.infra_synthesis.validator import SchemaValidator

    loader = SchemaLoader()
    validator = SchemaValidator()
    policy_engine = PolicyEngine()

    try:
        schema = loader.load(args.schema)
    except OSError as exc:
        print(f"ERROR: verify failed — {exc}", flush=True)
        logger.exception("verify failed: cannot load schema")
        return 1

    result = validator.validate(schema)
    if not result.valid:
        print("Schema validation FAILED:")
        for v in result.violations:
            print(f"  ✗ {v}")
        return 1

    print("Schema validation PASSED")

    policy_result = policy_engine.evaluate(schema)
    for _name, passed, message in policy_result.results:
        mark = "✓" if passed else "✗"
        print(f"  {mark} {message}")

    if not policy_result.passed:
        print("Policy evaluation FAILED")
        return 1

    print("Policy evaluation PASSED")
    return 0


def _cmd_deploy(args: argparse.Namespace) -> int:
    """Execute the ``deploy`` sub-command.

    Loads the schema, validates it, captures a pre-deploy snapshot, then
    runs the configured release strategy.

    Args:
        args: Parsed CLI namespace with ``schema`` and ``deploy_key`` attributes.

    Returns:
        Exit code (0 on success, 1 on error).

    """
    from thalos_prime.infra_synthesis.release.orchestrator import (
        ReleaseOrchestrator,
    )
    from thalos_prime.infra_synthesis.rollback.manager import RollbackManager
    from thalos_prime.infra_synthesis.schema_loader import SchemaLoader
    from thalos_prime.infra_synthesis.state.local import LocalStateBackend
    from thalos_prime.infra_synthesis.validator import SchemaValidator

    loader = SchemaLoader()
    validator = SchemaValidator()

    try:
        schema = loader.load(args.schema)
    except OSError as exc:
        print(f"ERROR: deploy failed — {exc}", flush=True)
        logger.exception("deploy failed: cannot load schema")
        return 1

    validation = validator.validate(schema)
    if not validation.valid:
        print("deploy aborted — schema validation failed:")
        for v in validation.violations:
            print(f"  ✗ {v}")
        return 1

    deploy_key = args.deploy_key
    backend = LocalStateBackend()
    rollback_manager = RollbackManager(backend)
    rollback_manager.pre_deploy(deploy_key, schema)

    orchestrator = ReleaseOrchestrator()
    try:
        orchestrator.deploy(schema, deploy_key)
    except ValueError as exc:
        print(f"ERROR: deploy failed — {exc}", flush=True)
        logger.exception("deploy failed")
        return 1

    print(f"Deploy complete for key '{deploy_key}'")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="thalos",
        description="Thalos Prime — autonomous infrastructure-synthesis CLI",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # build
    build_p = sub.add_parser("build", help="Generate provider artifacts from a schema")
    build_p.add_argument("--schema", required=True, help="Path to YAML schema file")
    build_p.add_argument("--out", required=True, help="Output directory for artifacts")

    # verify
    verify_p = sub.add_parser("verify", help="Validate schema and evaluate policies")
    verify_p.add_argument("--schema", required=True, help="Path to YAML schema file")

    # deploy
    deploy_p = sub.add_parser("deploy", help="Run the configured release strategy")
    deploy_p.add_argument("--schema", required=True, help="Path to YAML schema file")
    deploy_p.add_argument(
        "--deploy-key",
        default="latest",
        help="Deployment identifier for rollback snapshots (default: latest)",
    )

    return parser


def main() -> None:
    """Entry point for the ``thalos`` console script."""
    parser = _build_parser()
    args = parser.parse_args()
    _configure_logging(getattr(args, "verbose", False))

    handlers = {
        "build": _cmd_build,
        "verify": _cmd_verify,
        "deploy": _cmd_deploy,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(handler(args))


if __name__ == "__main__":
    main()
