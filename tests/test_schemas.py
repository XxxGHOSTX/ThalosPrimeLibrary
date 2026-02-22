"""Schema presence and sanity checks."""

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).parent.parent


def _load_schema(name: str) -> dict[str, Any]:
    path = ROOT / "schemas" / name
    with path.open("r", encoding="utf-8") as handle:
        return cast("dict[str, Any]", json.load(handle))


def test_hdr_schema_required_fields() -> None:
    """Verify the HDR schema enforces required identifiers and content hashes.

    The Human Direction Record (HDR) schema must declare exactly the five
    fields that establish authorship, intent, and content provenance:
    ``hdr_id``, ``author``, ``intent``, ``created_at``, and
    ``norm_content_hash``.  ``additionalProperties`` must be ``False`` so
    that the schema rejects any undeclared field at validation time.

    Example::

        schema = _load_schema("hdr.schema.json")
        assert schema["title"] == "Human Direction Record"
        assert "hdr_id" in schema["required"]
    """
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
    """Verify the ExecutionGraph schema declares nodes, edges, and provenance.

    The Execution Graph schema must expose a ``nodes`` array whose items
    carry at minimum ``node_id`` and ``type`` properties, plus a
    ``metadata.provenance`` object that records the origin of the graph.
    These constraints guarantee that every serialised graph can be traced
    back to its source and replayed deterministically.

    Example::

        schema = _load_schema("execution_graph.schema.json")
        assert schema["title"] == "Execution Graph"
        assert "nodes" in schema["properties"]
    """
    schema = _load_schema("execution_graph.schema.json")
    assert schema["title"] == "Execution Graph"
    assert "nodes" in schema["properties"]
    node_props = schema["properties"]["nodes"]["items"]["properties"]
    assert {"node_id", "type"}.issubset(node_props.keys())
    assert schema["properties"]["metadata"]["properties"]["provenance"]["type"] == "object"

