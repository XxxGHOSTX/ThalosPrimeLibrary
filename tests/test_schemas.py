"""
Schema presence and sanity checks.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _load_schema(name: str) -> dict[str, object]:
    path = ROOT / "schemas" / name
    with path.open("r", encoding="utf-8") as handle:
        result: dict[str, object] = json.load(handle)
        return result


def test_hdr_schema_required_fields() -> None:
    """HDR schema enforces required identifiers and hashes."""
    schema = _load_schema("hdr.schema.json")
    assert schema["title"] == "Human Direction Record"
    required = schema["required"]
    assert isinstance(required, list)
    assert set(required) == {
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
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert "nodes" in properties
    nodes = properties["nodes"]
    assert isinstance(nodes, dict)
    items = nodes["items"]
    assert isinstance(items, dict)
    node_props = items["properties"]
    assert isinstance(node_props, dict)
    assert {"node_id", "type"}.issubset(node_props.keys())
    metadata = properties["metadata"]
    assert isinstance(metadata, dict)
    meta_props = metadata["properties"]
    assert isinstance(meta_props, dict)
    provenance = meta_props["provenance"]
    assert isinstance(provenance, dict)
    assert provenance["type"] == "object"

