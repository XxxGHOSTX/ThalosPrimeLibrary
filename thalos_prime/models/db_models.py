"""
SQLAlchemy database models for Thalos Prime

These models define the database schema for persistent storage.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid


Base = declarative_base()


def generate_uuid():
    """Generate a new UUID string"""
    return str(uuid.uuid4())


class User(Base):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=generate_uuid, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    api_key = Column(String(64), unique=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


class Session(Base):
    """Session model for tracking user sessions"""
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, default=generate_uuid, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_activity = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    metadata = Column(JSON, default=dict, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    queries = relationship("Query", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_session_activity', 'is_active', 'last_activity'),
    )
    
    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', user_id={self.user_id})>"


class Query(Base):
    """Query model for tracking search queries"""
    __tablename__ = 'queries'
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=generate_uuid, nullable=False, index=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    query_text = Column(Text, nullable=False)
    search_mode = Column(String(20), nullable=False, default='hybrid')
    max_results = Column(Integer, nullable=False, default=10)
    results_count = Column(Integer, nullable=False, default=0)
    avg_score = Column(Float, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    cached = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    metadata = Column(JSON, default=dict, nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="queries")
    user = relationship("User", back_populates="queries")
    results = relationship("CachedResult", back_populates="query", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_query_created', 'created_at'),
        Index('idx_query_mode', 'search_mode', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Query(query_text='{self.query_text[:50]}...', mode='{self.search_mode}')>"


class CachedResult(Base):
    """Cached search result model"""
    __tablename__ = 'cached_results'
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey('queries.id'), nullable=False, index=True)
    address_hex = Column(String(255), nullable=False, index=True)
    page_text = Column(Text, nullable=False)
    snippet = Column(Text, nullable=True)
    coherence_score = Column(Float, nullable=False)
    language_score = Column(Float, nullable=True)
    structure_score = Column(Float, nullable=True)
    ngram_score = Column(Float, nullable=True)
    exact_match_score = Column(Float, nullable=True)
    confidence_level = Column(String(20), nullable=True)
    source = Column(String(20), nullable=False, default='local')
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)
    metadata = Column(JSON, default=dict, nullable=True)
    
    # Relationships
    query = relationship("Query", back_populates="results")
    
    __table_args__ = (
        Index('idx_result_score', 'coherence_score'),
        Index('idx_result_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<CachedResult(address='{self.address_hex[:20]}...', score={self.coherence_score})>"


class GeneratedPage(Base):
    """Generated page model for storing locally generated pages"""
    __tablename__ = 'generated_pages'
    
    id = Column(Integer, primary_key=True, index=True)
    address_hex = Column(String(255), unique=True, nullable=False, index=True)
    page_text = Column(Text, nullable=False)
    validation_status = Column(Boolean, default=True, nullable=False)
    generation_time_ms = Column(Float, nullable=True)
    access_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_accessed = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    metadata = Column(JSON, default=dict, nullable=True)
    
    __table_args__ = (
        Index('idx_page_accessed', 'last_accessed'),
        Index('idx_page_access_count', 'access_count'),
    )
    
    def __repr__(self):
        return f"<GeneratedPage(address='{self.address_hex[:20]}...', accesses={self.access_count})>"


class APILog(Base):
    """API request log model"""
    __tablename__ = 'api_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    endpoint = Column(String(100), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False, index=True)
    response_time_ms = Column(Float, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    metadata = Column(JSON, default=dict, nullable=True)
    
    __table_args__ = (
        Index('idx_log_endpoint_time', 'endpoint', 'created_at'),
        Index('idx_log_status', 'status_code', 'created_at'),
    )
    
    def __repr__(self):
        return f"<APILog(endpoint='{self.endpoint}', status={self.status_code})>"


def create_tables(engine):
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def drop_tables(engine):
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)
