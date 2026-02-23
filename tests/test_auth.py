"""Tests for the APIKeyAuthenticator authentication module.

Covers lifecycle methods (initialize, validate, operate, reconcile,
checkpoint, terminate), the authenticate() method, disabled-auth mode,
and the DeterministicHalt exception for misconfigured states.
"""

import pytest

from thalos_prime.auth.api_key import APIKeyAuthenticator, DeterministicHalt


def test_initialize_with_env_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """initialize() loads keys from THALOS_API_KEYS environment variable."""
    monkeypatch.setenv("THALOS_API_KEYS", "key-alpha,key-beta")
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)

    auth = APIKeyAuthenticator()
    auth.initialize()

    assert auth.authenticate("key-alpha")
    assert auth.authenticate("key-beta")
    assert not auth.authenticate("key-gamma")


def test_initialize_with_extra_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """initialize() merges extra_keys with environment keys."""
    monkeypatch.setenv("THALOS_API_KEYS", "env-key")
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)

    auth = APIKeyAuthenticator(extra_keys=["extra-key"])
    auth.initialize()

    assert auth.authenticate("env-key")
    assert auth.authenticate("extra-key")


def test_initialize_no_keys_raises_halt(monkeypatch: pytest.MonkeyPatch) -> None:
    """initialize() raises DeterministicHalt when auth is enabled but no keys configured."""
    monkeypatch.setenv("THALOS_API_KEYS", "")
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)

    auth = APIKeyAuthenticator()
    with pytest.raises(DeterministicHalt):
        auth.initialize()


def test_initialize_auth_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """initialize() succeeds with no keys when THALOS_AUTH_DISABLED=1."""
    monkeypatch.setenv("THALOS_AUTH_DISABLED", "1")
    monkeypatch.setenv("THALOS_API_KEYS", "")

    auth = APIKeyAuthenticator()
    auth.initialize()

    # All keys pass through when auth is disabled
    assert auth.authenticate("any-key")
    assert auth.authenticate("")
    assert auth.authenticate("bogus")


def test_validate_before_initialize_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """validate() raises DeterministicHalt if called before initialize()."""
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)

    auth = APIKeyAuthenticator()
    with pytest.raises(DeterministicHalt):
        auth.validate()


def test_validate_after_initialize_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """validate() succeeds after a successful initialize()."""
    monkeypatch.setenv("THALOS_API_KEYS", "valid-key")
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)

    auth = APIKeyAuthenticator()
    auth.initialize()
    auth.validate()  # Should not raise


def test_operate_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """operate() is a no-op and does not raise."""
    monkeypatch.setenv("THALOS_API_KEYS", "k1")
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)

    auth = APIKeyAuthenticator()
    auth.initialize()
    auth.operate()  # Should not raise


def test_reconcile_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """reconcile() is a no-op and does not raise."""
    monkeypatch.setenv("THALOS_API_KEYS", "k1")
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)

    auth = APIKeyAuthenticator()
    auth.initialize()
    auth.reconcile()  # Should not raise


def test_checkpoint_returns_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """checkpoint() returns a dictionary with configuration state."""
    monkeypatch.setenv("THALOS_API_KEYS", "k1,k2")
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)

    auth = APIKeyAuthenticator()
    auth.initialize()
    state = auth.checkpoint()

    assert state["component"] == "APIKeyAuthenticator"
    assert state["initialized"] is True
    assert state["auth_disabled"] is False
    assert state["key_count"] == 2


def test_terminate_clears_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """terminate() clears keys from memory and resets initialized flag."""
    monkeypatch.setenv("THALOS_API_KEYS", "k1")
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)

    auth = APIKeyAuthenticator()
    auth.initialize()
    assert auth.authenticate("k1")

    auth.terminate()

    # After terminate, authenticate raises because not initialized
    with pytest.raises(DeterministicHalt):
        auth.authenticate("k1")


def test_authenticate_before_initialize_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """authenticate() raises DeterministicHalt if called before initialize()."""
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)

    auth = APIKeyAuthenticator()
    with pytest.raises(DeterministicHalt):
        auth.authenticate("key")


def test_whitespace_keys_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    """initialize() strips whitespace from comma-separated key values."""
    monkeypatch.setenv("THALOS_API_KEYS", " key-a , key-b ")
    monkeypatch.delenv("THALOS_AUTH_DISABLED", raising=False)

    auth = APIKeyAuthenticator()
    auth.initialize()

    assert auth.authenticate("key-a")
    assert auth.authenticate("key-b")
    assert not auth.authenticate(" key-a ")


def test_deterministic_halt_message() -> None:
    """DeterministicHalt carries the message attribute."""
    halt = DeterministicHalt("test invariant violated")
    assert halt.message == "test invariant violated"
    assert str(halt) == "test invariant violated"
