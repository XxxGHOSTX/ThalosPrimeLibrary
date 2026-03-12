"""Infra-synthesis orchestration engine.

Control Plane component: coordinates the full artifact-generation pipeline.

Pipeline stages:
    1. Load schema via :class:`SchemaLoader`.
    2. Validate schema via :class:`SchemaValidator`.
    3. Run each adapter to write provider artifacts.
    4. Hash all artifacts via :class:`Hasher`.
    5. Emit ``"generated"`` and ``"hashed"`` events on the :class:`EventBus`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from thalos_prime.infra_synthesis.adapters.cloudflare import CloudflareAdapter
from thalos_prime.infra_synthesis.adapters.docker import DockerAdapter
from thalos_prime.infra_synthesis.adapters.github_actions import GitHubActionsAdapter
from thalos_prime.infra_synthesis.adapters.opentofu import OpenTofuAdapter
from thalos_prime.infra_synthesis.adapters.terraform import TerraformAdapter
from thalos_prime.infra_synthesis.events.bus import EventBus
from thalos_prime.infra_synthesis.hasher import Hasher
from thalos_prime.infra_synthesis.schema_loader import SchemaLoader
from thalos_prime.infra_synthesis.validator import SchemaValidator

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result of a single engine run.

    Attributes:
        schema: Validated schema dict that was processed.
        artifacts: All files written by adapters.
        manifest: SHA-256 digest mapping written to artifact_manifest.json.
        out_dir: Root output directory.

    """

    schema: dict[str, Any]
    artifacts: list[Path]
    manifest: dict[str, str]
    out_dir: Path


class InfraSynthesisEngine:
    """Orchestrates schema loading, validation, adapter execution, and hashing.

    Usage::

        engine = InfraSynthesisEngine()
        result = engine.generate(schema_path="schemas/infra.schema.yaml", out_dir="dist")

    The engine emits two events on its internal :class:`EventBus`:
    * ``"generated"`` — after all adapters have written files.
    * ``"hashed"``    — after the artifact manifest has been written.
    """

    def __init__(self) -> None:
        """Initialise the engine with default adapters and an empty event bus."""
        self._loader = SchemaLoader()
        self._validator = SchemaValidator()
        self._hasher = Hasher()
        self._bus = EventBus()
        self._adapters: list[
            TerraformAdapter
            | OpenTofuAdapter
            | CloudflareAdapter
            | GitHubActionsAdapter
            | DockerAdapter
        ] = [
            TerraformAdapter(),
            OpenTofuAdapter(),
            CloudflareAdapter(),
            GitHubActionsAdapter(),
            DockerAdapter(),
        ]

    @property
    def event_bus(self) -> EventBus:
        """Return the engine's event bus for external subscriptions.

        Returns:
            The internal :class:`EventBus` instance.

        """
        return self._bus

    def generate(
        self,
        schema_path: str | Path,
        out_dir: str | Path,
    ) -> GenerationResult:
        """Run the full artifact-generation pipeline.

        Args:
            schema_path: Path to the YAML schema file.
            out_dir: Root directory for all output artifacts.

        Returns:
            :class:`GenerationResult` with artifacts and manifest.

        Raises:
            SchemaLoadError: When the schema cannot be loaded.
            ValueError: When the schema fails validation.

        """
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # 1. Load
        schema = self._loader.load(schema_path)
        logger.info("Schema loaded from '%s'", schema_path)

        # 2. Validate
        validation = self._validator.validate(schema)
        if not validation.valid:
            msg = "Schema validation failed:\n" + "\n".join(
                f"  • {v}" for v in validation.violations
            )
            raise ValueError(msg)

        # 3. Generate artifacts
        all_artifacts: list[Path] = []
        for adapter in self._adapters:
            written = adapter.generate(schema, out_path)
            all_artifacts.extend(written)
            logger.debug(
                "Adapter '%s' wrote %d file(s)", type(adapter).__name__, len(written)
            )

        self._bus.publish("generated", {"artifact_count": len(all_artifacts)})

        # 4. Hash
        manifest = self._hasher.hash_artifacts(all_artifacts, out_path)

        self._bus.publish("hashed", {"manifest": manifest})

        logger.info(
            "InfraSynthesisEngine: generation complete — %d artifacts hashed",
            len(all_artifacts),
        )

        return GenerationResult(
            schema=schema,
            artifacts=all_artifacts,
            manifest=manifest,
            out_dir=out_path,
        )


__all__ = ["GenerationResult", "InfraSynthesisEngine"]
