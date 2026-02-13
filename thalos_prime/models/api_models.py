"""Pydantic models for API request/response validation.

These models define the schema for all API endpoints.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator


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


# Chat Endpoint Models
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    session_id: str | None = Field(None, description="Session ID for conversation continuity")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results to return")
    mode: SearchMode = Field(default=SearchMode.HYBRID, description="Search mode")

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        """Validate message is not empty."""
        empty_message_error = "Message cannot be empty or whitespace only"
        if not v.strip():
            raise ValueError(empty_message_error)
        return v.strip()

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "message": "hello world",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "max_results": 5,
                "mode": "hybrid",
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    reply: str = Field(..., description="Bot reply message")
    session_id: str = Field(..., description="Session ID")
    results: list[PageResult] = Field(default_factory=list, description="Search results")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "reply": "Found 5 results for your query...",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "results": [],
                "metadata": {"query_time_ms": 150},
            }
        }


# Search Endpoint Models
class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum results")
    mode: SearchMode = Field(default=SearchMode.HYBRID, description="Search mode")
    min_score: float = Field(default=0.0, ge=0, le=100, description="Minimum coherence score")

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        """Validate query is not empty."""
        empty_query_error = "Query cannot be empty or whitespace only"
        if not v.strip():
            raise ValueError(empty_query_error)
        return v.strip()

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "query": "the meaning of life",
                "max_results": 10,
                "mode": "hybrid",
                "min_score": 40.0,
            }
        }


class SearchResponse(BaseModel):
    """Response model for search endpoint."""

    query: str = Field(..., description="Original query")
    results: list[PageResult] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total results found")
    mode: SearchMode = Field(..., description="Search mode used")
    cached: bool = Field(default=False, description="Whether results were cached")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "query": "test query",
                "results": [],
                "total_found": 10,
                "mode": "hybrid",
                "cached": False,
                "metadata": {"search_time_ms": 250},
            }
        }


# Generate Endpoint Models
class GenerateRequest(BaseModel):
    """Request model for generate endpoint."""

    address: str | None = Field(None, description="Hex address to generate from")
    query: str | None = Field(None, description="Query to convert to address")
    validate: bool = Field(default=True, description="Whether to validate generated page")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "address": "abc123def456",
                "validate": True,
            }
        }


class GenerateResponse(BaseModel):
    """Response model for generate endpoint."""

    address: AddressInfo = Field(..., description="Page address")
    text: str = Field(..., description="Generated page text")
    valid: bool = Field(..., description="Whether page passed validation")
    generation_time_ms: float = Field(..., description="Generation time in milliseconds")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "address": {
                    "hex_address": "abc123",
                    "url": "https://libraryofbabel.info/book.cgi?hex=abc123",
                },
                "text": "generated page text...",
                "valid": True,
                "generation_time_ms": 0.5,
            }
        }


# Enumerate Endpoint Models
class EnumerateRequest(BaseModel):
    """Request model for enumerate endpoint."""

    query: str = Field(..., min_length=1, max_length=1000, description="Query to enumerate")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum addresses")
    depth: int = Field(default=1, ge=1, le=10, description="Enumeration depth")

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        """Validate query is not empty."""
        empty_query_error = "Query cannot be empty or whitespace only"
        if not v.strip():
            raise ValueError(empty_query_error)
        return v.strip()

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "query": "hello world",
                "max_results": 10,
                "depth": 2,
            }
        }


class EnumerateResponse(BaseModel):
    """Response model for enumerate endpoint."""

    query: str = Field(..., description="Original query")
    addresses: list[dict[str, Any]] = Field(..., description="Enumerated addresses")
    total_found: int = Field(..., description="Total addresses found")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "query": "hello world",
                "addresses": [
                    {"address": "abc123", "ngrams": ["hello", "world"], "score": 0.85}
                ],
                "total_found": 10,
                "metadata": {"enumeration_time_ms": 5.0},
            }
        }


# Decode Endpoint Models
class DecodeRequest(BaseModel):
    """Request model for decode endpoint."""

    address: str = Field(..., description="Page address")
    text: str = Field(..., min_length=1, description="Page text to decode")
    query: str | None = Field(None, description="Query for relevance scoring")
    normalization: NormalizationMode = Field(
        default=NormalizationMode.HEURISTIC, description="Normalization mode"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "address": "abc123",
                "text": "page text to analyze...",
                "query": "test query",
                "normalization": "heuristic",
            }
        }


class DecodeResponse(BaseModel):
    """Response model for decode endpoint."""

    address: AddressInfo = Field(..., description="Page address")
    raw_text: str = Field(..., description="Original text")
    normalized_text: str | None = Field(None, description="Normalized text if applied")
    coherence: CoherenceInfo = Field(..., description="Coherence analysis")
    provenance: ProvenanceInfo = Field(..., description="Provenance information")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "address": {"hex_address": "abc123"},
                "raw_text": "original text...",
                "normalized_text": None,
                "coherence": {"overall_score": 65.0, "confidence_level": "medium"},
                "provenance": {
                    "address": "abc123",
                    "source": "local",
                    "timestamp": 1707768000.0,
                },
            }
        }


# Status and Error Models
class StatusResponse(BaseModel):
    """Response model for status endpoint."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    features: dict[str, bool] = Field(default_factory=dict, description="Available features")

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "uptime_seconds": 3600.0,
                "features": {
                    "local_generation": True,
                    "remote_search": True,
                    "llm_normalization": False,
                },
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid request parameters",
                "details": {"field": "query", "issue": "cannot be empty"},
                "timestamp": "2026-02-12T20:00:00Z",
            }
        }

