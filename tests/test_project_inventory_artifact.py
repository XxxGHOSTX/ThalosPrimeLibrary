"""Tests for the project-inventory artifact adapter."""

from pathlib import Path

from thalos_prime.experiments import ProjectInventoryBuilder, project_inventory_to_artifact


def test_inventory_is_saved_as_pending_artifact(tmp_path: Path) -> None:
    """Inventory metadata can be passed into the existing artifact workflow."""
    (tmp_path / "README.md").write_text("inventory fixture", encoding="utf-8")
    inventory = ProjectInventoryBuilder().scan(tmp_path)
    artifact = project_inventory_to_artifact(inventory, timestamp_ns=123456789)
    assert artifact.validation_status.value == "pending"
    assert artifact.metadata["artifact_kind"] == "project_inventory"
    assert artifact.metadata["project_digest"] == inventory.project_digest
    assert artifact.timestamp_ns == 123456789
    assert artifact.source_uris == []
