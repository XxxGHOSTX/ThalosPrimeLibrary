"""Root pytest configuration for Thalos Prime Library."""

from __future__ import annotations

import pytest

collect_ignore_glob: list[str] = []

try:
    import fastapi  # noqa: F401
except ImportError:
    collect_ignore_glob += [
        "tests/test_api_chat.py",
        "tests/test_api_search.py",
        "tests/test_babel_endpoints.py",
        "tests/test_main.py",
    ]


# Fake test-only secrets. Never use these values in any deployment.
@pytest.fixture(autouse=True)
def _configure_test_only_thalos_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THALOS_API_TOKEN", "test-token-for-thalos-prime-tests-only")
    monkeypatch.setenv("THALOS_ADMIN_API_KEY", "test-admin-key-for-thalos-prime-only-0001")
    monkeypatch.setenv("THALOS_PRP_KEY", "test-prp-key-for-thalos-prime-only-0001")
    monkeypatch.setenv("THALOS_NEXUS_SIGNING_KEY", "test-signing-key-for-thalos-prime-only-0001")
