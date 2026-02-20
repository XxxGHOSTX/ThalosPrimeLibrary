"""Database Connection Manager.

Handles SQLAlchemy database connections, session management, and pooling.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from thalos_prime.api.config import config
from thalos_prime.models.db_models import Base

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions.

    Provides connection pooling, session management, and database initialization.
    """

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize database manager.

        Args:
            database_url: Database connection URL (uses config if not provided)

        """
        self.database_url = database_url or config.database_url
        self.engine: Engine | None = None
        self.SessionLocal: Any = None
        self._initialized = False

    def init_engine(self) -> None:
        """Initialize SQLAlchemy engine with connection pooling."""
        if self._initialized:
            logger.warning("Database already initialized")
            return

        logger.info(f"Initializing database: {self.database_url}")

        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            echo=False  # Set to True for SQL logging
        )

        # Add event listeners
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn: object, connection_record: object) -> None:
            logger.debug("Database connection established")

        @event.listens_for(self.engine, "checkout")
        def receive_checkout(
            dbapi_conn: object,
            connection_record: object,
            connection_proxy: object,
        ) -> None:
            logger.debug("Database connection checked out from pool")

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        self._initialized = True
        logger.info("Database engine initialized successfully")

    def create_tables(self) -> None:
        """Create all database tables."""
        if not self.engine:
            self.init_engine()

        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")

    def drop_tables(self) -> None:
        """Drop all database tables (use with caution!)."""
        if not self.engine:
            self.init_engine()

        logger.warning("Dropping all database tables!")
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped")

    @contextmanager
    def get_session(self) -> Iterator[Session]:
        """Get a database session (context manager).

        Usage:
            with db_manager.get_session() as session:
                # Use session here
                session.query(...)

        Yields:
            SQLAlchemy Session object

        """
        if not self._initialized:
            self.init_engine()

        if self.SessionLocal is None:
            msg = "SessionLocal is not initialized"
            raise RuntimeError(msg)

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.exception(f"Session error: {e}")
            raise
        finally:
            session.close()

    def initialize(self) -> None:
        """Initialize the database manager by setting up the engine.

        Calls init_engine() to establish the connection pool and session factory.
        """
        self.init_engine()

    def validate(self) -> None:
        """Validate that the database manager is properly initialized.

        Raises:
            RuntimeError: If not initialized or engine is None.

        """
        if not self._initialized:
            msg = "DatabaseManager is not initialized; call initialize() first"
            raise RuntimeError(msg)
        if self.engine is None:
            msg = "DatabaseManager engine is None after initialization"
            raise RuntimeError(msg)
        logger.info("DatabaseManager validation passed")

    def operate(self) -> None:
        """Ensure database tables exist, creating them if necessary."""
        if self._initialized:
            self.create_tables()
        logger.info("DatabaseManager operating")

    def reconcile(self) -> None:
        """Reconcile database state by disposing and reinitializing the engine if needed."""
        if self.engine is not None:
            logger.info("DatabaseManager reconciling: disposing engine")
            self.engine.dispose()
            self._initialized = False
        self.init_engine()
        logger.info("DatabaseManager reconciliation complete")

    def checkpoint(self) -> None:
        """Log the current state of the database manager as a checkpoint."""
        logger.info(
            "DatabaseManager checkpoint: initialized=%s engine=%s",
            self._initialized,
            self.engine,
        )

    def terminate(self) -> None:
        """Terminate the database manager and release all resources."""
        self.close()

    def close(self) -> None:
        """Close database engine and connections."""
        if self.engine:
            logger.info("Closing database connections...")
            self.engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")


# Global database manager instance
_db_manager = None


def init_database(database_url: str | None = None) -> DatabaseManager:
    """Initialize global database manager.

    Args:
        database_url: Database connection URL

    Returns:
        DatabaseManager instance

    """
    global _db_manager

    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
        _db_manager.init_engine()
        _db_manager.create_tables()

    return _db_manager


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance.

    Returns:
        DatabaseManager instance

    Raises:
        RuntimeError: If database not initialized

    """
    global _db_manager

    if _db_manager is None:
        msg = "Database not initialized. Call init_database() first."
        raise RuntimeError(msg)

    return _db_manager


@contextmanager
def get_db_session() -> Iterator[Session]:
    """Get database session (convenience function).

    Usage:
        with get_db_session() as session:
            users = session.query(User).all()

    Yields:
        SQLAlchemy Session

    """
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session


def close_database() -> None:
    """Close global database connections."""
    global _db_manager

    if _db_manager:
        _db_manager.close()
        _db_manager = None
