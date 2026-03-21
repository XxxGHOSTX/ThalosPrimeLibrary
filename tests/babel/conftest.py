"""Pytest fixtures for Babel subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from thalos_prime.babel.control.semantic_orchestrator import SemanticOrchestrator

if TYPE_CHECKING:
    from pathlib import Path


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
