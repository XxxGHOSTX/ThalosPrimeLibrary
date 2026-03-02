"""Thalos NEXUS — Nucleus: genome ingestion, validation, hashing, signing.

The nucleus is the entry point for all genome data.  It:

1. Loads a JSON genome file containing ``intent``, ``policy``, ``fitness``,
   and ``lineages`` sections.
2. Validates each section against the bundled JSON schemas.
3. Computes a deterministic SHA-256 hash of the serialised bundle.
4. Signs the hash with HMAC-SHA256 using a key derived from the
   ``THALOS_NEXUS_SIGNING_KEY`` environment variable (falls back to the
   development default ``"thalos-nexus-dev-key-v1"``).
5. Returns a ``GenomeBundle`` dataclass capturing all of the above.

Control Plane boundary: this module performs ingestion and signing only.
No gate execution or output-file management belongs here.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEV_SIGNING_KEY = "thalos-nexus-dev-key-v1"
_SCHEMAS_DIR = Path(__file__).parent / "schemas"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GenomeValidationError(ValueError):
    """Raised when a genome section fails JSON-schema validation."""


class GenomeLoadError(OSError):
    """Raised when the genome file cannot be read or parsed."""


# ---------------------------------------------------------------------------
# GenomeBundle
# ---------------------------------------------------------------------------


@dataclass
class GenomeBundle:
    """Immutable container for a validated, signed genome.

    Attributes
    ----------
    genome_id:
        Unique identifier taken from ``intent.id``.
    genome_hash:
        SHA-256 hex digest of the canonical JSON serialisation of the bundle
        (``intent`` + ``policy`` + ``fitness`` + ``lineages``).
    signature:
        HMAC-SHA256 hex digest of ``genome_hash``, keyed by the signing key.
    intent:
        Validated intent section.
    policy:
        Validated policy section.
    fitness:
        Validated fitness section.
    lineages:
        Validated lineages list.
    created_at:
        ISO-8601 UTC timestamp of bundle creation.

    """

    genome_id: str
    genome_hash: str
    signature: str
    intent: dict[str, Any]
    policy: dict[str, Any]
    fitness: dict[str, Any]
    lineages: list[Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise the bundle to a plain dictionary."""
        return {
            "genome_id": self.genome_id,
            "genome_hash": self.genome_hash,
            "signature": self.signature,
            "intent": self.intent,
            "policy": self.policy,
            "fitness": self.fitness,
            "lineages": self.lineages,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_schema(name: str) -> dict[str, Any]:
    """Load a bundled JSON schema by filename."""
    schema_path = _SCHEMAS_DIR / name
    with schema_path.open(encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[no-any-return]


def _validate_section(data: object, schema_name: str) -> None:
    """Validate *data* against the named schema.

    Raises
    ------
    GenomeValidationError
        If validation fails.

    """
    schema = _load_schema(schema_name)
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        msg = f"Genome section failed schema '{schema_name}': {exc.message}"
        raise GenomeValidationError(msg) from exc


def _canonical_json(obj: object) -> str:
    """Return a deterministic JSON string (sorted keys, no extra whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(data: str) -> str:
    """Return the SHA-256 hex digest of *data* encoded as UTF-8."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _hmac_sha256_hex(key: str, message: str) -> str:
    """Return HMAC-SHA256 hex digest of *message* using *key*."""
    return hmac.new(
        key.encode("utf-8"),
        message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_genome(genome_path: str | Path) -> GenomeBundle:
    """Load, validate, hash, and sign a genome file.

    The genome file must be a JSON object with the following top-level keys:

    - ``intent``   — conforms to ``intent.schema.json``
    - ``policy``   — conforms to ``policy.schema.json``
    - ``fitness``  — conforms to ``fitness.schema.json``
    - ``lineages`` — conforms to ``lineages.schema.json``

    The signing key is read from the ``THALOS_NEXUS_SIGNING_KEY`` environment
    variable; if absent the development default is used.

    Parameters
    ----------
    genome_path:
        Path to the JSON genome file.

    Returns
    -------
    GenomeBundle
        Validated and signed genome bundle.

    Raises
    ------
    GenomeLoadError
        If the file cannot be read or is not valid JSON.
    GenomeValidationError
        If any section fails its JSON-schema check.

    """
    path = Path(genome_path)
    try:
        raw = path.read_text(encoding="utf-8")
        genome_data: dict[str, Any] = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"Cannot load genome file '{path}': {exc}"
        raise GenomeLoadError(msg) from exc

    for section in ("intent", "policy", "fitness", "lineages"):
        if section not in genome_data:
            msg = f"Genome file missing required section '{section}'"
            raise GenomeValidationError(msg)

    _validate_section(genome_data["intent"], "intent.schema.json")
    _validate_section(genome_data["policy"], "policy.schema.json")
    _validate_section(genome_data["fitness"], "fitness.schema.json")
    _validate_section(genome_data["lineages"], "lineages.schema.json")

    bundle_canonical = _canonical_json(
        {
            "intent": genome_data["intent"],
            "policy": genome_data["policy"],
            "fitness": genome_data["fitness"],
            "lineages": genome_data["lineages"],
        }
    )
    genome_hash = _sha256_hex(bundle_canonical)

    signing_key = os.environ.get("THALOS_NEXUS_SIGNING_KEY", _DEV_SIGNING_KEY)
    signature = _hmac_sha256_hex(signing_key, genome_hash)

    return GenomeBundle(
        genome_id=str(genome_data["intent"]["id"]),
        genome_hash=genome_hash,
        signature=signature,
        intent=genome_data["intent"],
        policy=genome_data["policy"],
        fitness=genome_data["fitness"],
        lineages=genome_data["lineages"],
        created_at=datetime.now(UTC).isoformat(),
    )
