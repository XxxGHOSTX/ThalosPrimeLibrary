"""Pydantic models for API request/response validation.

These models define the schema for all API endpoints.
"""

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
                "provenance": {
                    "address": "abc123",
                    "source": "local",
                    "timestamp": 1707768000.0,
                },
            }
        }


class GenerateRequest(BaseModel):
    """Request model for page generation."""

    address: str | None = Field(None, description="Hex address to generate page for")
    query: str | None = Field(None, description="Query to convert to address")
    validate_page: bool = Field(default=False, description="Whether to validate the generated page")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "address": "abc123def456",
                "query": None,
                "validate_page": False,
            }
        }


class GenerateResponse(BaseModel):
    """Response model for page generation."""

    address: AddressInfo = Field(..., description="Page address information")
    text: str = Field(..., description="Generated page text")
    valid: bool = Field(..., description="Whether the page passed validation")
    generation_time_ms: float = Field(..., description="Time taken to generate in milliseconds")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "address": {"hex_address": "abc123def456"},
                "text": "the quick brown fox...",
                "valid": True,
                "generation_time_ms": 12.5,
            }
        }


class SearchRequest(BaseModel):
    """Request model for search."""

    query: str = Field(..., description="Search query")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    mode: SearchMode = Field(default=SearchMode.LOCAL, description="Search mode")
    min_score: float = Field(default=0.0, ge=0, le=100, description="Minimum coherence score filter")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "query": "the quick brown fox",
                "max_results": 10,
                "mode": "local",
                "min_score": 0.0,
            }
        }


class SearchResponse(BaseModel):
    """Response model for search."""

    query: str = Field(..., description="Original search query")
    results: list[PageResult] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total number of results found")
    mode: SearchMode = Field(..., description="Search mode used")
    cached: bool = Field(default=False, description="Whether results were served from cache")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "query": "the quick brown fox",
                "results": [],
                "total_found": 0,
                "mode": "local",
                "cached": False,
                "metadata": {"query_time_ms": 5.2},
            }
        }


class EnumerateRequest(BaseModel):
    """Request model for address enumeration."""

    query: str = Field(..., description="Query to enumerate addresses for")
    max_results: int = Field(default=10, ge=1, le=1000, description="Maximum number of addresses")
    depth: int = Field(default=1, ge=1, le=5, description="Enumeration depth")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "query": "the quick brown fox",
                "max_results": 10,
                "depth": 1,
            }
        }


class EnumerateResponse(BaseModel):
    """Response model for address enumeration."""

    query: str = Field(..., description="Original query")
    addresses: list[dict[str, Any]] = Field(..., description="Enumerated addresses with metadata")
    total_found: int = Field(..., description="Total number of addresses found")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "query": "the quick brown fox",
                "addresses": [{"address": "abc123", "score": 0.85}],
                "total_found": 1,
                "metadata": {"enumeration_time_ms": 2.1},
            }
        }


class DecodeRequest(BaseModel):
    """Request model for page decoding."""

    address: str = Field(..., description="Page address")
    text: str = Field(..., description="Page text to decode")
    query: str | None = Field(None, description="Optional query for relevance scoring")
    normalization: NormalizationMode = Field(
        default=NormalizationMode.NONE, description="Normalization mode to apply"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "address": "abc123def456",
                "text": "the quick brown fox...",
                "query": "fox",
                "normalization": "none",
            }
        }


class DecodeResponse(BaseModel):
    """Response model for page decoding."""

    address: AddressInfo = Field(..., description="Page address information")
    raw_text: str = Field(..., description="Raw page text")
    normalized_text: str | None = Field(None, description="Normalized text if requested")
    coherence: CoherenceInfo = Field(..., description="Coherence analysis results")
    provenance: ProvenanceInfo = Field(..., description="Provenance information")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "address": {"hex_address": "abc123def456"},
                "raw_text": "the quick brown fox...",
                "normalized_text": None,
                "coherence": {"overall_score": 75.5, "confidence_level": "medium"},
                "provenance": {"address": "abc123", "source": "user_provided", "timestamp": 1707768000.0},
            }
        }


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., description="User message")
    session_id: str | None = Field(None, description="Optional session ID for continuity")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum number of results to include")
    mode: str = Field(default="local", description="Search mode (local/hybrid/remote)")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "message": "Tell me about the library of babel",
                "session_id": None,
                "max_results": 5,
                "mode": "local",
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    reply: str = Field(..., description="Bot reply message")
    session_id: str = Field(..., description="Session ID for continuity")
    results: list[PageResult] = Field(default_factory=list, description="Relevant page results")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "reply": "Found 3 results for your query.",
                "session_id": "abc123",
                "results": [],
                "metadata": {"query_time_ms": 15.3},
            }
        }


class StatusResponse(BaseModel):
    """Response model for status/health endpoints."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional status details")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "uptime_seconds": 3600.0,
                "details": {},
            }
        }


class ErrorResponse(BaseModel):
    """Response model for error responses."""

    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "error": "ValidationError",
                "message": "Request validation failed",
                "details": {"field": "query", "issue": "required"},
            }
        }
