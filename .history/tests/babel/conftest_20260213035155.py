"""
Pytest fixtures for Babel subsystem.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from thalos_prime.babel.control.semantic_orchestrator import SemanticOrchestrator


@pytest.fixture
def temp_storage(tmp_path: Path) -> Path:
    storage = tmp_path / "storage"
    storage.mkdir()
    return storage


@pytest.fixture
def test_orchestrator(temp_storage: Path) -> SemanticOrchestrator:
    orch = SemanticOrchestrator(temp_storage)
    orch.initialize()
    return orch
