"""Pydantic models for API request/response validation.

These models define the schema for all API endpoints.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator
from typing import Any

from pydantic import BaseModel, Field, validator

class SearchMode(StrEnum):
    """Search mode: local generation or remote fetch."""

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

# ... (Rest of code unchanged, ensure to apply same fix if unmatched braces are found elsewhere)
