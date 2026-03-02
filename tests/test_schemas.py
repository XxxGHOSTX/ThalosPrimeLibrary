"""
Schema presence and sanity checks.
"""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent


def _load_schema(name: str) -> dict[str, Any]:
    path = ROOT / "schemas" / name
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        msg = f"Schema {name!r} must be a JSON object"
        raise ValueError(msg)
    return data


def test_load_schema_rejects_non_dict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-object schemas are rejected."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    invalid = schemas_dir / "invalid.schema.json"
    invalid.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)
    with pytest.raises(ValueError, match="must be a JSON object"):
        _load_schema("invalid.schema.json")


def test_hdr_schema_required_fields() -> None:
    """HDR schema enforces required identifiers and hashes."""
    schema = _load_schema("hdr.schema.json")
    assert schema["title"] == "Human Direction Record"
    assert set(schema["required"]) == {
        "hdr_id",
        "author",
        "intent",
        "created_at",
        "norm_content_hash",
    }
    assert schema["additionalProperties"] is False


def test_execution_graph_schema_minimum_shape() -> None:
    """Execution graph schema declares nodes, edges, and versioning."""
    schema = _load_schema("execution_graph.schema.json")
    assert schema["title"] == "Execution Graph"
    assert "nodes" in schema["properties"]
    node_props = schema["properties"]["nodes"]["items"]["properties"]
    assert {"node_id", "type"}.issubset(node_props.keys())
    assert schema["properties"]["metadata"]["properties"]["provenance"]["type"] == "object"
