"""Pydantic models for API request/response validation.

These models define the schema for all API endpoints.
"""

from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class SearchMode(StrEnum):
    """Search mode: local generation, remote fetch, hybrid, or generative."""

    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"
    GENERATIVE = "generative"


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


class RemoteAccessPolicy(StrEnum):
    """Policy for allowing remote/federated retrieval in search."""

    LOCAL_ONLY = "local_only"
    CONSENT_REQUIRED = "consent_required"
    ALLOW_REMOTE = "allow_remote"
    ALWAYS_ALLOW = "always_allow"


# Address Information
class AddressInfo(BaseModel):
    """Library of Babel address information."""

    hex_address: str = Field(..., description="Hexadecimal address")
    wall: int | None = Field(None, description="Wall number")
    shelf: int | None = Field(None, description="Shelf number")
    volume: int | None = Field(None, description="Volume number")
    page: int | None = Field(None, description="Page number")
    url: str | None = Field(None, description="Full URL to page")

    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra={
            "example": {
                "hex_address": "abc123def456",
                "wall": 1,
                "shelf": 2,
                "volume": 3,
                "page": 4,
                "url": "https://libraryofbabel.info/book.cgi?hex=abc123def456",
            }
        }
    )


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

    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra={
            "example": {
                "overall_score": 86.5,
                "language_score": 82.0,
                "structure_score": 84.0,
                "ngram_score": 82.0,
                "exact_match_score": 100.0,
                "confidence_level": "high",
                "metrics": {"word_count": 150, "sentence_count": 8},
            }
        }
    )


# Provenance Information
class ProvenanceInfo(BaseModel):
    """Provenance tracking information."""

    address: str = Field(..., description="Page address")
    source: str = Field(..., description="Source (local/remote)")
    query: str | None = Field(None, description="Original query")
    timestamp: float = Field(..., description="Generation timestamp")
    normalized: bool = Field(default=False, description="Whether normalization was applied")
    llm_provider: str | None = Field(None, description="LLM provider if used")

    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra={
            "example": {
                "address": "abc123",
                "source": "local",
                "query": "test query",
                "timestamp": 1707768000.0,
                "normalized": False,
                "llm_provider": None,
            }
        }
    )


# Page Result
class PageResult(BaseModel):
    """Single page result with scores."""

    address: AddressInfo = Field(..., description="Page address information")
    text: str = Field(..., description="Page text content (3200 chars)")
    snippet: str | None = Field(None, description="Short snippet preview")
    coherence: CoherenceInfo = Field(..., description="Coherence scoring")
    provenance: ProvenanceInfo = Field(..., description="Provenance information")
    normalized_text: str | None = Field(None, description="Normalized text if available")

    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra={
            "example": {
                "address": {
                    "hex_address": "abc123",
                    "url": "https://libraryofbabel.info/book.cgi?hex=abc123",
                },
                "text": "the quick brown fox...",
                "snippet": "the quick brown fox...",
                "coherence": {"overall_score": 75.5, "confidence_level": "medium"},
                "provenance": {
                    "address": "abc123",
                    "source": "local",
                    "timestamp": 1707768000.0,
                },
            }
        }
    )


# Error Response
class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error code or type")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")


# Status Response
class StatusResponse(BaseModel):
    """API status response."""

    status: str = Field(..., description="API status")
    message: str = Field(..., description="Status message")
    version: str = Field(..., description="API version")
    timestamp: float = Field(..., description="Response timestamp")


# Search Request/Response
class SearchRequest(BaseModel):
    """Search request parameters."""

    query: str = Field(..., min_length=1, description="Search query")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum results to return")
    mode: SearchMode = Field(default=SearchMode.HYBRID, description="Search mode")
    min_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Minimum coherence score")
    remote_access_policy: RemoteAccessPolicy = Field(
        default=RemoteAccessPolicy.CONSENT_REQUIRED,
        description="Remote retrieval policy",
    )
    remote_consent: bool = Field(
        default=False,
        description="Explicit user consent for remote retrieval when policy requires it",
    )
    enable_query_expansion: bool = Field(
        default=True,
        description="Enable deterministic query variant expansion (always-on by default)",
    )
    enable_diversity_rerank: bool = Field(
        default=True,
        description="Enable diversity-aware reranking (always-on by default)",
    )
    enable_adaptive_optimization: bool = Field(
        default=True,
        description="Enable intent-aware adaptive optimization (always-on by default)",
    )
    diversity_lambda: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Diversity weight for reranking (0=relevance only, 1=diversity only)",
    )


class SearchResponse(BaseModel):
    """Search response with results and metadata."""

    query: str = Field(..., description="Original query")
    results: list[PageResult] = Field(..., description="Matching page results")
    total_found: int = Field(..., description="Total results found")
    mode: SearchMode = Field(..., description="Search mode used")
    cached: bool = Field(default=False, description="Whether result was served from cache")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Query metadata")


# Chat Request/Response
class ChatRequest(BaseModel):
    """Chat request parameters."""

    message: str = Field(..., min_length=1, description="User message")
    session_id: str | None = Field(None, description="Existing session ID (optional)")
    mode: SearchMode = Field(
        default=SearchMode.HYBRID,
        description="Search mode: local, remote, hybrid, or generative",
    )
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results to include")
    min_score: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Minimum coherence score (0-100). Default 80. System halts with state capture when unmet.",
    )


class ChatResponse(BaseModel):
    """Chat response with reply and results."""

    reply: str = Field(..., description="Bot reply message")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    results: list[PageResult] = Field(..., description="Relevant page results")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Response metadata")


# Generate Request/Response
class GenerateRequest(BaseModel):
    """Page generation request parameters."""

    address: str | None = Field(None, description="Hexadecimal address to generate from")
    query: str | None = Field(None, description="Query to convert to address")
    validate_page: bool = Field(default=False, description="Whether to validate the generated page")


class GenerateResponse(BaseModel):
    """Generated page response."""

    address: AddressInfo = Field(..., description="Page address information")
    text: str = Field(..., description="Generated page text")
    valid: bool = Field(..., description="Whether the page passed validation")
    generation_time_ms: float = Field(..., description="Generation time in milliseconds")


# Enumerate Request/Response
class EnumerateRequest(BaseModel):
    """Address enumeration request parameters."""

    query: str = Field(..., min_length=1, description="Query to enumerate addresses for")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum addresses to return")
    depth: int = Field(default=2, ge=1, le=5, description="Enumeration depth")


class EnumerateResponse(BaseModel):
    """Address enumeration response."""

    query: str = Field(..., description="Original query")
    addresses: list[dict[str, Any]] = Field(..., description="Enumerated addresses with scores")
    total_found: int = Field(..., description="Total addresses found")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Enumeration metadata")


# Decode Request/Response
class DecodeRequest(BaseModel):
    """Page decode request parameters."""

    address: str = Field(..., description="Page address")
    text: str = Field(..., description="Page text to decode")
    query: str | None = Field(None, description="Optional query for relevance scoring")
    normalization: NormalizationMode = Field(
        default=NormalizationMode.NONE,
        description="Text normalization mode",
    )


class DecodeResponse(BaseModel):
    """Decoded page response with coherence analysis."""

    address: AddressInfo = Field(..., description="Page address information")
    raw_text: str = Field(..., description="Original page text")
    normalized_text: str | None = Field(None, description="Normalized text if requested")
    coherence: CoherenceInfo = Field(..., description="Coherence scoring")
    provenance: ProvenanceInfo = Field(..., description="Provenance information")
