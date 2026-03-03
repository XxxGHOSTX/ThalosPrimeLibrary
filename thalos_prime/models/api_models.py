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

class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(..., description="User message")
    session_id: str | None = Field(None, description="Optional session ID")
    mode: str = Field(default="local", description="Search mode")
    max_results: int = Field(default=5, ge=1, le=50, description="Max results")


class ChatResponse(BaseModel):
    """Chat response model."""

    reply: str = Field(..., description="Bot reply")
    session_id: str = Field(..., description="Session ID")
    results: list[PageResult] = Field(default_factory=list, description="Search results")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")


class DecodeRequest(BaseModel):
    """Decode request model."""

    address: str = Field(..., description="Page address")
    text: str = Field(..., description="Page text")
    query: str | None = Field(None, description="Optional query")
    normalization: NormalizationMode = Field(default=NormalizationMode.NONE, description="Normalization mode")


class DecodeResponse(BaseModel):
    """Decode response model."""

    address: AddressInfo = Field(..., description="Page address")
    raw_text: str = Field(..., description="Raw page text")
    normalized_text: str | None = Field(None, description="Normalized text")
    coherence: CoherenceInfo = Field(..., description="Coherence scores")
    provenance: ProvenanceInfo = Field(..., description="Provenance info")


class EnumerateRequest(BaseModel):
    """Enumerate request model."""

    query: str = Field(..., description="Query string")
    max_results: int = Field(default=10, ge=1, le=100, description="Max results")
    depth: int = Field(default=2, ge=1, le=5, description="Search depth")


class EnumerateResponse(BaseModel):
    """Enumerate response model."""

    query: str = Field(..., description="Original query")
    addresses: list[dict[str, Any]] = Field(..., description="Found addresses")
    total_found: int = Field(..., description="Total addresses found")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")


class GenerateRequest(BaseModel):
    """Generate request model."""

    address: str | None = Field(None, description="Hex address")
    query: str | None = Field(None, description="Query to convert")
    validate_page: bool = Field(default=True, description="Validate generated page")


class GenerateResponse(BaseModel):
    """Generate response model."""

    address: AddressInfo = Field(..., description="Page address")
    text: str = Field(..., description="Generated page text")
    valid: bool = Field(..., description="Whether page is valid")
    generation_time_ms: float = Field(..., description="Generation time in ms")


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., description="Search query")
    max_results: int = Field(default=10, ge=1, le=100, description="Max results")
    mode: SearchMode = Field(default=SearchMode.LOCAL, description="Search mode")
    min_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Minimum coherence score")


class SearchResponse(BaseModel):
    """Search response model."""

    query: str = Field(..., description="Original query")
    results: list[PageResult] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total results found")
    mode: SearchMode = Field(..., description="Search mode used")
    cached: bool = Field(default=False, description="Whether result was cached")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Error details")


class StatusResponse(BaseModel):
    """Status response model."""

    status: str = Field(..., description="System status")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Uptime in seconds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")

