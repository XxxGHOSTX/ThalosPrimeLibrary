"""Thalos Prime authentication subsystem.

Exports the APIKeyAuthenticator and DeterministicHalt for use throughout
the Thalos Prime API and control plane.
"""

from thalos_prime.auth.api_key import APIKeyAuthenticator, DeterministicHalt

__all__ = ["APIKeyAuthenticator", "DeterministicHalt"]
