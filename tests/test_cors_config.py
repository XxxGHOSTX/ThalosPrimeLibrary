"""Tests for CORS origin allowlist enforcement."""
import pytest

from thalos_prime.cors_config import get_configured_cors_origins


def test_development_defaults_are_loopback_only():
    assert get_configured_cors_origins(environment="development", raw_origins=None) == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_comma_separated_origins_are_trimmed():
    assert get_configured_cors_origins(
        environment="production",
        raw_origins="https://app.example.test, https://admin.example.test ",
    ) == ["https://app.example.test", "https://admin.example.test"]


def test_production_without_explicit_origins_fails_closed():
    with pytest.raises(ValueError, match="explicitly configured"):
        get_configured_cors_origins(environment="production", raw_origins=None)


def test_wildcard_origin_is_rejected():
    with pytest.raises(ValueError, match="Wildcard"):
        get_configured_cors_origins(environment="production", raw_origins="*")


def test_origin_without_http_scheme_is_rejected():
    with pytest.raises(ValueError, match="http:// or https://"):
        get_configured_cors_origins(environment="production", raw_origins="app.example.test")
