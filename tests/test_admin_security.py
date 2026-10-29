"""Tests for fail-closed administrative API-key configuration."""
import pytest
from fastapi import HTTPException

from thalos_prime.api.routes.admin import verify_admin_key


def test_admin_auth_fails_closed_without_strong_configured_key(monkeypatch):
    monkeypatch.delenv("THALOS_ADMIN_API_KEY", raising=False)
    with pytest.raises(HTTPException) as raised:
        verify_admin_key("anything")
    assert raised.value.status_code == 503


def test_admin_auth_accepts_configured_token(monkeypatch):
    token = "test-only-admin-token-with-at-least-32-utf8-bytes"
    monkeypatch.setenv("THALOS_ADMIN_API_KEY", token)
    assert verify_admin_key(token) is True


def test_admin_auth_rejects_wrong_token(monkeypatch):
    token = "test-only-admin-token-with-at-least-32-utf8-bytes"
    monkeypatch.setenv("THALOS_ADMIN_API_KEY", token)
    with pytest.raises(HTTPException) as raised:
        verify_admin_key("not-the-configured-token")
    assert raised.value.status_code == 401
