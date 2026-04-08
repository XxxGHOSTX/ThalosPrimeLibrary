"""SQLAlchemy session provider for the Knowledge Engine.

Lifecycle-managed session factory backed by SQLAlchemy 2.0.
Defaults to SQLite in-memory for testing; configure db_url for production.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from thalos_prime.knowledge_engine.db.models import Base

logger = logging.getLogger(__name__)


class SessionProvider:
    """Lifecycle-managed SQLAlchemy session provider.

    Manages database engine and session factory lifecycle.

    Example::

        provider = SessionProvider("sqlite:///:memory:")
        provider.initialize()
        provider.validate()
        with provider.session() as sess:
            sess.add(...)
        provider.terminate()

    """

    def __init__(self, db_url: str = "sqlite:///:memory:") -> None:
        """Initialize the session provider.

        Args:
            db_url: SQLAlchemy database URL. Defaults to in-memory SQLite.

        """
        self._db_url = db_url
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None
        self._initialized: bool = False

    def initialize(self) -> None:
        """Create the engine, create all tables, and set up session factory.

        Raises:
            RuntimeError: If the engine cannot be created.

        """
        self._engine = create_engine(self._db_url, echo=False)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(self._engine, expire_on_commit=False)
        self._initialized = True
        logger.info("SessionProvider initialized: db_url=%s", self._db_url)

    def validate(self) -> None:
        """Verify that the engine is alive and tables are accessible.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized or self._engine is None:
            msg = "SessionProvider.validate(): not initialized — call initialize() first"
            raise RuntimeError(msg)
        with self._engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.debug("SessionProvider validation passed")

    def operate(self) -> None:
        """No-op: sessions are obtained via the session() context manager."""
        logger.debug("SessionProvider.operate(): no-op — use session() context manager")

    def reconcile(self) -> None:
        """Verify that all ORM tables exist; recreate missing ones.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized or self._engine is None:
            msg = "SessionProvider.reconcile(): not initialized"
            raise RuntimeError(msg)
        Base.metadata.create_all(self._engine)
        logger.info("SessionProvider.reconcile(): tables verified/created")

    def checkpoint(self) -> dict[str, object]:
        """Serialize current provider state.

        Returns:
            Dictionary with db_url and initialization status.

        """
        return {
            "component": "SessionProvider",
            "db_url": self._db_url,
            "initialized": self._initialized,
        }

    def terminate(self) -> None:
        """Dispose the engine and clear the session factory."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
        self._session_factory = None
        self._initialized = False
        logger.info("SessionProvider terminated")

    @contextlib.contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Context manager yielding a database session.

        Yields:
            An active SQLAlchemy Session.

        Raises:
            RuntimeError: If not initialized.

        """
        if not self._initialized or self._session_factory is None:
            msg = "SessionProvider.session(): not initialized — call initialize() first"
            raise RuntimeError(msg)
        sess = self._session_factory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()
