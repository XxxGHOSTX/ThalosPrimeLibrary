"""Pydantic models for API request/response validation.

These models define the schema for all API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class SearchMode(StrEnum):
    """Search mode: local generation or remote fetch."""

    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"

class NormalizationMode(StrEnum):
    """Text normalization mode."""

    NONE = "none"
    HEURISTIC = "heuristic"
    LLM = "llm"

class ConfidenceLevel(StrEnum):
    """Coherence confidence level."""

    HIGH = "high"
    MEDIUM = "medium"
    SPARSE = "sparse"
    MINIMAL = "minimal"

# Address Information
class AddressInfo(BaseModel):
    """Library of Babel address information."""

    hex_address: str = Field(..., description="Hexadecimal address")
    wall: int | None = Field(None, description="Wall number")
    shelf: int | None = Field(None, description="Shelf number")
    volume: int | None = Field(None, description="Volume number")
    page: int | None = Field(None, description="Page number")
    url: str | None = Field(None, description="Full URL to page")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "hex_address": "abc123def456",
                "wall": 1,
                "shelf": 2,
                "volume": 3,
                "page": 4,
                "url": "https://libraryofbabel.info/book.cgi?hex=abc123def456",
            }
        }

# Coherence Information
class CoherenceInfo(BaseModel):
    """Coherence scoring information."""

    overall_score: float = Field(..., ge=0, le=100, description="Overall coherence score (0-100)")
    language_score: float = Field(..., ge=0, le=100, description="Language detection score")
    structure_score: float = Field(..., ge=0, le=100, description="Structure analysis score")
    ngram_score: float = Field(..., ge=0, le=100, description="N-gram coherence score")
    exact_match_score: float = Field(..., ge=0, le=100, description="Exact match score")
    confidence_level: ConfidenceLevel = Field(..., description="Confidence level")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Additional metrics")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "overall_score": 75.5,
                "language_score": 65.0,
                "structure_score": 55.0,
                "ngram_score": 45.0,
                "exact_match_score": 100.0,
                "confidence_level": "medium",
                "metrics": {"word_count": 150, "sentence_count": 8},
            }
        }

# Provenance Information
class ProvenanceInfo(BaseModel):
    """Provenance tracking information."""

    address: str = Field(..., description="Page address")
    source: str = Field(..., description="Source (local/remote)")
    query: str | None = Field(None, description="Original query")
    timestamp: float = Field(..., description="Generation timestamp")
    normalized: bool = Field(default=False, description="Whether normalization was applied")
    llm_provider: str | None = Field(None, description="LLM provider if used")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "address": "abc123",
                "source": "local",
                "query": "test query",
                "timestamp": 1707768000.0,
                "normalized": False,
                "llm_provider": None,
            }
        }

# Page Result
class PageResult(BaseModel):
    """Single page result with scores."""

    address: AddressInfo = Field(..., description="Page address information")
    text: str = Field(..., description="Page text content (3200 chars)")
    snippet: str | None = Field(None, description="Short snippet preview")
    coherence: CoherenceInfo = Field(..., description="Coherence scoring")
    provenance: ProvenanceInfo = Field(..., description="Provenance information")
    normalized_text: str | None = Field(None, description="Normalized text if available")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "address": {
                    "hex_address": "abc123",
                    "url": "https://libraryofbabel.info/book.cgi?hex=abc123",
                },
                "text": "the quick brown fox...",
                "snippet": "the quick brown fox...",
                "coherence": {"overall_score": 75.5, "confidence_level": "medium"},
                "provenance": {"address": "abc123", "source": "local", "timestamp": 1707768000.0},
            }
        }


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """Request to search for pages matching a query."""

    query: str = Field(..., min_length=1, description="Search query")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    mode: SearchMode = Field(default=SearchMode.LOCAL, description="Search mode")
    min_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Minimum coherence score")


class SearchResponse(BaseModel):
    """Response from search endpoint."""

    query: str = Field(..., description="Original query")
    results: list[PageResult] = Field(default_factory=list, description="Search results")
    total_found: int = Field(..., description="Total number of results found")
    mode: SearchMode = Field(..., description="Search mode used")
    cached: bool = Field(default=False, description="Whether result came from cache")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class GenerateRequest(BaseModel):
    """Request to generate a Library of Babel page."""

    address: str | None = Field(None, description="Explicit hex address to generate")
    query: str | None = Field(None, description="Query to convert to address")
    validate_page: bool = Field(default=True, description="Whether to validate the generated page")


class GenerateResponse(BaseModel):
    """Response from generate endpoint."""

    address: AddressInfo = Field(..., description="Generated page address")
    text: str = Field(..., description="Generated page text")
    valid: bool = Field(..., description="Whether the page is valid")
    generation_time_ms: float = Field(..., description="Generation time in milliseconds")


class EnumerateRequest(BaseModel):
    """Request to enumerate addresses for a query."""

    query: str = Field(..., min_length=1, description="Query to enumerate addresses for")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of addresses")
    depth: int = Field(default=2, ge=1, le=5, description="Enumeration depth")


class EnumerateResponse(BaseModel):
    """Response from enumerate endpoint."""

    query: str = Field(..., description="Original query")
    addresses: list[dict[str, Any]] = Field(default_factory=list, description="Enumerated addresses")
    total_found: int = Field(..., description="Total number of addresses found")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DecodeRequest(BaseModel):
    """Request to decode and score a page."""

    address: str = Field(..., description="Page address")
    text: str = Field(..., description="Page text to decode")
    query: str | None = Field(None, description="Optional query for context scoring")
    normalization: NormalizationMode = Field(
        default=NormalizationMode.NONE,
        description="Normalization mode to apply",
    )


class DecodeResponse(BaseModel):
    """Response from decode endpoint."""

    address: AddressInfo = Field(..., description="Page address information")
    raw_text: str = Field(..., description="Raw page text")
    normalized_text: str | None = Field(None, description="Normalized text if requested")
    coherence: CoherenceInfo = Field(..., description="Coherence scoring")
    provenance: ProvenanceInfo = Field(..., description="Provenance information")
    normalization_mode: NormalizationMode = Field(
        default=NormalizationMode.NONE,
        description="Normalization mode applied",
    )
    decode_time_ms: float = Field(default=0.0, description="Decode time in milliseconds")


class ChatRequest(BaseModel):
    """Request for conversational chat endpoint."""

    message: str = Field(..., min_length=1, description="User message")
    session_id: str | None = Field(None, description="Optional session ID for continuity")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results to include")
    mode: str = Field(default="local", description="Search mode: local, hybrid")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    reply: str = Field(..., description="Assistant reply message")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    results: list[PageResult] = Field(default_factory=list, description="Relevant page results")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class StatusResponse(BaseModel):
    """API status response."""

    status: str = Field(..., description="API status")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    message: str = Field(default="", description="Optional status message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Request to register a new user."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class RegisterResponse(BaseModel):
    """Response after successful registration."""

    user_id: str = Field(..., description="New user UUID")
    username: str = Field(..., description="Registered username")
    email: str = Field(..., description="Registered email")
    message: str = Field(default="Registration successful", description="Success message")


class LoginRequest(BaseModel):
    """Request to login and obtain a JWT token."""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Response after successful login containing JWT token."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user_id: str = Field(..., description="User UUID")
    username: str = Field(..., description="Username")
    subscription_tier: str = Field(default="free", description="User subscription tier")


class UserProfile(BaseModel):
    """Authenticated user profile."""

    user_id: str = Field(..., description="User UUID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    subscription_tier: str = Field(default="free", description="Subscription tier")
    is_active: bool = Field(default=True, description="Whether account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")


# ---------------------------------------------------------------------------
# Subscription / PayPal models
# ---------------------------------------------------------------------------


class SubscriptionTier(StrEnum):
    """Available subscription tiers."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class CreateOrderRequest(BaseModel):
    """Request to create a PayPal order."""

    tier: SubscriptionTier = Field(..., description="Subscription tier to purchase")
    return_url: str = Field(..., description="URL to redirect after approval")
    cancel_url: str = Field(..., description="URL to redirect on cancellation")


class CreateOrderResponse(BaseModel):
    """Response with PayPal order details."""

    order_id: str = Field(..., description="PayPal order ID")
    approval_url: str = Field(..., description="URL for user to approve the payment")
    status: str = Field(..., description="Order status")


class CaptureOrderRequest(BaseModel):
    """Request to capture an approved PayPal order."""

    order_id: str = Field(..., description="PayPal order ID to capture")


class CaptureOrderResponse(BaseModel):
    """Response after capturing a PayPal order."""

    order_id: str = Field(..., description="PayPal order ID")
    status: str = Field(..., description="Capture status")
    subscription_tier: str = Field(..., description="Activated subscription tier")
    message: str = Field(default="Payment successful", description="Status message")


class SubscriptionStatus(BaseModel):
    """Current subscription status for a user."""

    user_id: str = Field(..., description="User UUID")
    tier: SubscriptionTier = Field(..., description="Current subscription tier")
    is_active: bool = Field(default=True, description="Whether subscription is active")
    expires_at: datetime | None = Field(None, description="Subscription expiry date")
    features: list[str] = Field(default_factory=list, description="Enabled features")

