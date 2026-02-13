"""
Database Connection Manager

Handles SQLAlchemy database connections, session management, and pooling.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from contextlib import contextmanager
from typing import Optional, Iterator, Any
import logging

from thalos_prime.api.config import config
from thalos_prime.models.db_models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and sessions.
    
    Provides connection pooling, session management, and database initialization.
    """
    
    def __init__(self, database_url: Optional[str] = None) -> None:
        """
        Initialize database manager.
        
        Args:
            database_url: Database connection URL (uses config if not provided)
        """
        self.database_url = database_url or config.database_url
        self.engine: Optional[Engine] = None
        self.SessionLocal: Any = None
        self._initialized = False
    
    def init_engine(self) -> None:
        """Initialize SQLAlchemy engine with connection pooling"""
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
        def receive_connect(dbapi_conn: Any, connection_record: Any) -> None:
            logger.debug("Database connection established")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn: Any, connection_record: Any, connection_proxy: Any) -> None:
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
        """Create all database tables"""
        if not self.engine:
            self.init_engine()
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    def drop_tables(self) -> None:
        """Drop all database tables (use with caution!)"""
        if not self.engine:
            self.init_engine()
        
        logger.warning("Dropping all database tables!")
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped")
    
    @contextmanager
    def get_session(self) -> Iterator[Session]:
        """
        Get a database session (context manager).
        
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
            raise RuntimeError("SessionLocal is not initialized")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            session.close()
    
    def close(self) -> None:
        """Close database engine and connections"""
        if self.engine:
            logger.info("Closing database connections...")
            self.engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")


# Global database manager instance
_db_manager = None


def init_database(database_url: Optional[str] = None) -> DatabaseManager:
    """
    Initialize global database manager.
    
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
    """
    Get global database manager instance.
    
    Returns:
        DatabaseManager instance
    
    Raises:
        RuntimeError: If database not initialized
    """
    global _db_manager
    
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    return _db_manager


@contextmanager
def get_db_session() -> Iterator[Session]:
    """
    Get database session (convenience function).
    
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
    """Close global database connections"""
    global _db_manager
    
    if _db_manager:
        _db_manager.close()
        _db_manager = None
