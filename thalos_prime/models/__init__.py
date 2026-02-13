"""
Thalos Prime Data Models

Pydantic models for request/response validation and SQLAlchemy models for database.
"""

from thalos_prime.models.api_models import (
    ChatRequest,
    ChatResponse,
    SearchRequest,
    SearchResponse,
    GenerateRequest,
    GenerateResponse,
    EnumerateRequest,
    EnumerateResponse,
    DecodeRequest,
    DecodeResponse,
    StatusResponse,
    ErrorResponse,
    PageResult,
    AddressInfo,
    CoherenceInfo,
    ProvenanceInfo
)

from thalos_prime.models.db_models import (
    Base,
    User,
    Session,
    Query,
    CachedResult,
    GeneratedPage,
    create_tables,
    drop_tables
)

__all__ = [
    # API Models
    'ChatRequest',
    'ChatResponse',
    'SearchRequest',
    'SearchResponse',
    'GenerateRequest',
    'GenerateResponse',
    'EnumerateRequest',
    'EnumerateResponse',
    'DecodeRequest',
    'DecodeResponse',
    'StatusResponse',
    'ErrorResponse',
    'PageResult',
    'AddressInfo',
    'CoherenceInfo',
    'ProvenanceInfo',
    # DB Models
    'Base',
    'User',
    'Session',
    'Query',
    'CachedResult',
    'GeneratedPage',
    'create_tables',
    'drop_tables',
]
