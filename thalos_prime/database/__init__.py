"""Database package placeholder for Thalos Prime.
Define connections, repositories, and migrations here.
"""
"""Thalos Prime database subsystem.

Exports the SQLite-backed ResultStore for search result and session persistence,
alongside the SQLAlchemy-based DatabaseManager for optional ORM-driven storage.
"""

from thalos_prime.database.store import ResultStore  # noqa: E402

__all__ = ["ResultStore"]
