"""Thalos NEXUS — ER (Endoplasmic Reticulum): artifact folding and SBOM generation.

Provides:

- ``ArtifactFolder``: zips a list of file paths into a bundle and returns the
  output archive path.
- ``SBOMEntry``: a dataclass representing one SBOM entry.
- ``generate_sbom``: writes a simple JSON SBOM from a list of package specifiers.

All paths use ``pathlib.Path`` for Windows compatibility.

Control Plane boundary: artifact packaging only; no gate or spine logic here.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# SBOMEntry
# ---------------------------------------------------------------------------


@dataclass
class SBOMEntry:
    """A single entry in the Software Bill of Materials.

    Attributes
    ----------
    name:
        Package name (e.g. ``"requests"``).
    version:
        Package version string (e.g. ``"2.31.0"``).
    license:
        SPDX licence identifier or free-text licence name.

    """

    name: str
    version: str
    license: str


# ---------------------------------------------------------------------------
# ArtifactFolder
# ---------------------------------------------------------------------------


class ArtifactFolder:
    """Packages files into a zip archive and generates SBOM documents.

    Examples
    --------
    >>> folder = ArtifactFolder()
    >>> zip_path = folder.fold(files=["repro_manifest.json"], output_path="bundle.zip")
    >>> sbom_path = folder.generate_sbom(
    ...     packages=["requests==2.31.0:Apache-2.0"],
    ...     output_path="sbom.json",
    ... )

    """

    def fold(self, files: list[str], output_path: str) -> str:
        """Zip *files* into *output_path* and return the archive path.

        Files that do not exist are silently skipped; a warning is embedded in
        the archive as ``_missing.txt`` if any files were absent.

        Parameters
        ----------
        files:
            Absolute or relative paths to include in the archive.
        output_path:
            Destination path for the ``.zip`` file.

        Returns
        -------
        str
            The path to the created zip archive.

        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        missing: list[str] = []

        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in files:
                p = Path(file_path)
                if p.exists():
                    zf.write(p, p.name)
                else:
                    missing.append(str(p))
            if missing:
                zf.writestr("_missing.txt", "\n".join(missing))

        return str(out)

    def generate_sbom(self, packages: list[str], output_path: str) -> str:
        """Generate a JSON SBOM from a list of package specifiers.

        Each entry in *packages* is parsed as ``"name==version:license"`` or
        ``"name==version"`` (licence defaults to ``"UNKNOWN"``).

        Parameters
        ----------
        packages:
            Package specifiers, e.g. ``["requests==2.31.0:Apache-2.0"]``.
        output_path:
            Destination path for the SBOM JSON file.

        Returns
        -------
        str
            The path to the written SBOM file.

        """
        entries: list[SBOMEntry] = []
        for spec in packages:
            entry = _parse_package_spec(spec)
            entries.append(entry)

        sbom: dict[str, object] = {
            "schema_version": "1.0",
            "created_at": datetime.now(UTC).isoformat(),
            "components": [asdict(e) for e in entries],
        }
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(sbom, indent=2), encoding="utf-8")
        return str(out)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_package_spec(spec: str) -> SBOMEntry:
    """Parse a package specifier into a ``SBOMEntry``.

    Format: ``"name==version:license"`` or ``"name==version"`` or ``"name"``.
    """
    license_str = "UNKNOWN"
    if ":" in spec:
        pkg_part, license_str = spec.rsplit(":", 1)
    else:
        pkg_part = spec

    if "==" in pkg_part:
        name, version = pkg_part.split("==", 1)
    else:
        name, version = pkg_part, "UNKNOWN"

    return SBOMEntry(name=name.strip(), version=version.strip(), license=license_str.strip())
