"""Thalos Prime NEXUS Core v1 — CycloneDX SBOM Generator.

Attempts to generate a CycloneDX SBOM using ``cyclonedx-py``.  Falls back to
a minimal valid CycloneDX JSON SBOM if the tool is unavailable.

Control Plane boundary: artifact generation only — no lifecycle coordination.
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_FALLBACK_TOOLS: list[dict[str, str]] = [
    {"vendor": "thalos_nexus", "name": "sbom_generator", "version": "1.0.0"}
]


class SbomGenerator:
    """Generates a CycloneDX Software Bill of Materials for a project.

    Attempts to invoke ``cyclonedx-py`` as a subprocess.  If the tool is not
    installed or fails, a minimal valid CycloneDX JSON SBOM is written instead.
    """

    def generate(self, project_dir: Path, output_path: Path) -> str:
        """Generate a CycloneDX SBOM and write it to *output_path*.

        Args:
            project_dir: Root of the project to analyse.
            output_path: Destination path for the generated SBOM JSON file.

        Returns:
            SHA-256 hex digest of the written SBOM file.

        """
        success = self._try_cyclonedx(project_dir, output_path)
        if not success:
            logger.warning("cyclonedx-py unavailable or failed; writing minimal fallback SBOM")
            self._write_fallback(output_path)

        data = output_path.read_bytes()
        return hashlib.sha256(data).hexdigest()

    def _try_cyclonedx(self, project_dir: Path, output_path: Path) -> bool:
        """Attempt to run cyclonedx-py and write output to *output_path*.

        Args:
            project_dir: Project root.
            output_path: Destination path.

        Returns:
            ``True`` if the tool ran successfully, ``False`` otherwise.

        """
        cyclonedx_cmd = [
            sys.executable,
            "-m",
            "cyclonedx_py",
            "environment",
            "--output-format",
            "JSON",
            "--output-file",
            str(output_path),
        ]
        try:
            result = subprocess.run(
                cyclonedx_cmd,
                cwd=project_dir,
                capture_output=True,
                timeout=120,
                check=False,
            )
            if result.returncode == 0:
                logger.debug("cyclonedx-py succeeded: %s", output_path)
                return True
            logger.debug(
                "cyclonedx-py exited %d: %s",
                result.returncode,
                result.stderr.decode(errors="replace")[:200],
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("cyclonedx-py not available: %s", exc)
        return False

    @staticmethod
    def _write_fallback(output_path: Path) -> None:
        """Write a minimal valid CycloneDX JSON SBOM to *output_path*.

        Args:
            output_path: Destination file path.

        """
        sbom: dict[str, Any] = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "version": 1,
            "metadata": {
                "timestamp": datetime.now(UTC).isoformat(),
                "tools": _FALLBACK_TOOLS,
            },
            "components": [],
        }
        output_path.write_text(json.dumps(sbom, indent=2), encoding="utf-8")
