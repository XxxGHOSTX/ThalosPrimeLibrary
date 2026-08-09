"""Tests for knowledge_engine.db.session."""

from __future__ import annotations

import pytest

from thalos_prime.knowledge_engine.db.session import SessionProvider


def test_session_provider_lifecycle() -> None:
    provider = SessionProvider("sqlite:///:memory:")
    provider.initialize()
    provider.validate()
    provider.operate()
    provider.reconcile()
    cp = provider.checkpoint()
    assert cp["initialized"] is True
    provider.terminate()
    cp2 = provider.checkpoint()
    assert cp2["initialized"] is False


def test_session_context_manager() -> None:
    provider = SessionProvider("sqlite:///:memory:")
    provider.initialize()
    with provider.session() as sess:
        assert sess is not None
    provider.terminate()


def test_session_not_initialized_raises() -> None:
    provider = SessionProvider()
    with pytest.raises(RuntimeError, match="not initialized"):
        with provider.session():
            pass


def test_validate_not_initialized_raises() -> None:
    provider = SessionProvider()
    with pytest.raises(RuntimeError, match="not initialized"):
        provider.validate()


def test_reconcile_not_initialized_raises() -> None:
    provider = SessionProvider()
    with pytest.raises(RuntimeError, match="not initialized"):
        provider.reconcile()


def test_checkpoint_default() -> None:
    provider = SessionProvider()
    cp = provider.checkpoint()
    assert cp["component"] == "SessionProvider"
    assert cp["initialized"] is False


def test_terminate_idempotent() -> None:
    provider = SessionProvider("sqlite:///:memory:")
    provider.initialize()
    provider.terminate()
    provider.terminate()
