"""Thalos Prime Data Models.

Pydantic models for request/response validation and SQLAlchemy models for database.
"""

from thalos_prime.models.api_models import (
    AddressInfo,
    ChatRequest,
    ChatResponse,
    CoherenceInfo,
    DecodeRequest,
    DecodeResponse,
    EnumerateRequest,
    EnumerateResponse,
    ErrorResponse,
    GenerateRequest,
    GenerateResponse,
    PageResult,
    ProvenanceInfo,
    SearchRequest,
    SearchResponse,
    StatusResponse,
)

__all__ = [
    # API Models
    "AddressInfo",
    "ChatRequest",
    "ChatResponse",
    "CoherenceInfo",
    "DecodeRequest",
    "DecodeResponse",
    "EnumerateRequest",
    "EnumerateResponse",
    "ErrorResponse",
    "GenerateRequest",
    "GenerateResponse",
    "PageResult",
    "ProvenanceInfo",
    "SearchRequest",
    "SearchResponse",
    "StatusResponse",
]

# DB models require SQLAlchemy which is an optional dependency.
# Import conditionally so the API can run without a database.
# A bare ImportError catch is intentional here: SQLAlchemy and any of its
# transitive dependencies may be absent in lightweight deployments (e.g. Vercel).
try:
    from thalos_prime.models.db_models import (
        Base,
        CachedResult,
        GeneratedPage,
        Query,
        Session,
        User,
        create_tables,
        drop_tables,
    )

    __all__ += [
        "Base",
        "CachedResult",
        "GeneratedPage",
        "Query",
        "Session",
        "User",
        "create_tables",
        "drop_tables",
    ]
except ImportError:
    pass
