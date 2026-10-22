"""Tests for the project-inventory artifact adapter."""

from pathlib import Path

import pytest

from thalos_prime.experiments import ProjectInventoryBuilder, project_inventory_to_artifact


def test_inventory_is_saved_as_pending_artifact(tmp_path: Path) -> None:
    """Inventory metadata can be passed into the existing artifact workflow."""
    (tmp_path / "README.md").write_text("inventory fixture", encoding="utf-8")
    inventory = ProjectInventoryBuilder().scan(tmp_path)
    source_uri = tmp_path.resolve().as_uri()
    artifact = project_inventory_to_artifact(
        inventory,
        source_uri=source_uri,
        timestamp_ns=123456789,
    )
    assert artifact.validation_status.value == "pending"
    assert artifact.metadata["artifact_kind"] == "project_inventory"
    assert artifact.metadata["project_digest"] == inventory.project_digest
    assert artifact.timestamp_ns == 123456789
    assert artifact.source_uris == [source_uri]


def test_inventory_artifact_requires_real_source_uri(tmp_path: Path) -> None:
    """The adapter must not invent source provenance for an inventory."""
    (tmp_path / "README.md").write_text("inventory fixture", encoding="utf-8")
    inventory = ProjectInventoryBuilder().scan(tmp_path)
    with pytest.raises(ValueError, match="source_uri must identify"):
        project_inventory_to_artifact(inventory, source_uri=" ", timestamp_ns=123)
