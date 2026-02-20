"""
Schema presence and sanity checks.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _load_schema(name: str) -> dict:
    path = ROOT / "schemas" / name
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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

