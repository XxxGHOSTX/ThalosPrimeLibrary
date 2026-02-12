"""Tests for control plane lifecycle."""

import pytest

from configs.config import Settings
from src.control import ControlPlane, LifecycleState


@pytest.fixture
def test_settings(tmp_path: pytest.TempPathFactory) -> Settings:
    """Create test settings with temporary paths."""
    return Settings(
        corpus_dir=str(tmp_path / "corpus"),
        index_path=str(tmp_path / "data" / "index.pkl"),
        manifest_path=str(tmp_path / "data" / "manifest.json"),
        state_db_path=str(tmp_path / "data" / "state.db"),
        event_log_path=str(tmp_path / "data" / "events.jsonl"),
        checkpoint_dir=str(tmp_path / "data" / "checkpoints"),
    )


class TestControlPlane:
    """Test control plane lifecycle."""

    def test_initialization(self, test_settings: Settings) -> None:
        """Test control plane initialization."""
        cp = ControlPlane(test_settings)
        assert cp.state == LifecycleState.UNINITIALIZED

        cp.initialize()
        assert cp.state == LifecycleState.INITIALIZED
        assert cp.state_store is not None
        assert cp.event_log is not None

    def test_validation_without_index(self, test_settings: Settings) -> None:
        """Test validation fails without index."""
        cp = ControlPlane(test_settings)
        cp.initialize()

        result = cp.validate()
        assert result is False

    def test_validation_with_index(self, test_settings: Settings) -> None:
        """Test validation succeeds with index."""
        cp = ControlPlane(test_settings)
        cp.initialize()

        # Create dummy index and manifest
        test_settings.get_index_path().write_bytes(b"dummy index")
        test_settings.get_manifest_path().write_text('[]')

        result = cp.validate()
        assert result is True
        assert cp.state == LifecycleState.VALIDATED

    def test_operate_requires_validation(self, test_settings: Settings) -> None:
        """Test operate requires validation."""
        cp = ControlPlane(test_settings)
        cp.initialize()

        # Try to operate without validation
        cp.operate()
        # Should not change state without validation
        assert cp.state != LifecycleState.OPERATING

    def test_operate_after_validation(self, test_settings: Settings) -> None:
        """Test operate after validation."""
        cp = ControlPlane(test_settings)
        cp.initialize()

        # Create dummy files for validation
        test_settings.get_index_path().write_bytes(b"dummy index")
        test_settings.get_manifest_path().write_text('[]')

        cp.validate()
        cp.operate()

        assert cp.state == LifecycleState.OPERATING

    def test_checkpoint_creation(self, test_settings: Settings) -> None:
        """Test checkpoint creation."""
        cp = ControlPlane(test_settings)
        cp.initialize()

        # Create dummy files
        test_settings.get_index_path().write_bytes(b"dummy index")
        test_settings.get_manifest_path().write_text('[]')

        cp.validate()
        cp.operate()

        # Create checkpoint
        checkpoint_file = cp.checkpoint()

        assert checkpoint_file.exists()
        assert checkpoint_file.suffix == ".json"
        assert cp.state == LifecycleState.OPERATING

    def test_reconcile(self, test_settings: Settings) -> None:
        """Test reconciliation."""
        cp = ControlPlane(test_settings)
        cp.initialize()

        # Create dummy files
        test_settings.get_index_path().write_bytes(b"dummy index")
        test_settings.get_manifest_path().write_text('[]')

        cp.validate()
        cp.operate()

        # Reconcile should re-validate
        result = cp.reconcile()
        assert result is True
        assert cp.state == LifecycleState.OPERATING

    def test_terminate(self, test_settings: Settings) -> None:
        """Test termination."""
        cp = ControlPlane(test_settings)
        cp.initialize()

        cp.terminate()
        assert cp.state == LifecycleState.TERMINATED

    def test_get_state(self, test_settings: Settings) -> None:
        """Test get_state method."""
        cp = ControlPlane(test_settings)
        state = cp.get_state()

        assert "state" in state
        assert "validation_hashes" in state
        assert "initialized" in state
        assert "operating" in state
