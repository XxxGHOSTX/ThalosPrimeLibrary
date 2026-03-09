"""Thalos Prime Data Models.

Pydantic models for request/response validation and SQLAlchemy models for database.
"""

import contextlib

from thalos_prime.models.api_models import (
    AddressInfo,
    CaptureOrderRequest,
    CaptureOrderResponse,
    ChatRequest,
    ChatResponse,
    CoherenceInfo,
    CreateOrderRequest,
    CreateOrderResponse,
    DecodeRequest,
    DecodeResponse,
    EnumerateRequest,
    EnumerateResponse,
    ErrorResponse,
    GenerateRequest,
    GenerateResponse,
    LoginRequest,
    LoginResponse,
    PageResult,
    ProvenanceInfo,
    RegisterRequest,
    RegisterResponse,
    SearchRequest,
    SearchResponse,
    StatusResponse,
    SubscriptionStatus,
    SubscriptionTier,
    UserProfile,
)

# SQLAlchemy models are optional (not required for the API or Vercel deployment)
with contextlib.suppress(ImportError):
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

__all__ = [
    "AddressInfo",
    "Base",
    "CachedResult",
    "CaptureOrderRequest",
    "CaptureOrderResponse",
    "ChatRequest",
    "ChatResponse",
    "CoherenceInfo",
    "CreateOrderRequest",
    "CreateOrderResponse",
    "DecodeRequest",
    "DecodeResponse",
    "EnumerateRequest",
    "EnumerateResponse",
    "ErrorResponse",
    "GenerateRequest",
    "GenerateResponse",
    "GeneratedPage",
    "LoginRequest",
    "LoginResponse",
    "PageResult",
    "ProvenanceInfo",
    "Query",
    "RegisterRequest",
    "RegisterResponse",
    "SearchRequest",
    "SearchResponse",
    "Session",
    "StatusResponse",
    "SubscriptionStatus",
    "SubscriptionTier",
    "User",
    "UserProfile",
    "create_tables",
    "drop_tables",
]
