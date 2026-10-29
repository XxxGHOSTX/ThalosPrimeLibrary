"""Security-sensitive environment configuration tests."""

from __future__ import annotations

import pytest

from thalos_prime.api.config import load_config


def _clear_security_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("THALOS_SECRET_KEY", raising=False)
    monkeypatch.delenv("THALOS_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("THALOS_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)


def test_development_uses_ephemeral_key_and_localhost_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_security_env(monkeypatch)
    monkeypatch.setenv("THALOS_ENV", "development")
    config = load_config()
    assert len(config.secret_key.encode("utf-8")) >= 32
    assert "*" not in config.cors_origins
    assert all("localhost" in origin or "127.0.0.1" in origin for origin in config.cors_origins)


def test_production_requires_explicit_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_security_env(monkeypatch)
    monkeypatch.setenv("THALOS_ENV", "production")
    with pytest.raises(RuntimeError, match="THALOS_SECRET_KEY"):
        load_config()


def test_production_rejects_short_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_security_env(monkeypatch)
    monkeypatch.setenv("THALOS_ENV", "production")
    monkeypatch.setenv("THALOS_SECRET_KEY", "too-short")
    with pytest.raises(RuntimeError, match="at least 32"):
        load_config()


def test_production_requires_explicit_cors_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_security_env(monkeypatch)
    monkeypatch.setenv("THALOS_ENV", "production")
    monkeypatch.setenv("THALOS_SECRET_KEY", "p" * 48)
    with pytest.raises(RuntimeError, match="THALOS_CORS_ORIGINS"):
        load_config()


def test_production_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_security_env(monkeypatch)
    monkeypatch.setenv("THALOS_ENV", "production")
    monkeypatch.setenv("THALOS_SECRET_KEY", "p" * 48)
    monkeypatch.setenv("THALOS_CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="wildcard"):
        load_config()


def test_production_accepts_strong_secret_and_explicit_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_security_env(monkeypatch)
    monkeypatch.setenv("THALOS_ENV", "production")
    monkeypatch.setenv("THALOS_SECRET_KEY", "p" * 48)
    monkeypatch.setenv("THALOS_CORS_ORIGINS", "https://example.com,https://admin.example.com")
    config = load_config()
    assert config.secret_key == "p" * 48
    assert config.cors_origins == ["https://example.com", "https://admin.example.com"]
