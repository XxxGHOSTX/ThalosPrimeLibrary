"""
API Configuration Module

Configuration settings for the Thalos Prime API.
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """API Configuration"""
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=4, description="Number of worker processes")
    reload: bool = Field(default=False, description="Enable auto-reload")
    
    # Database settings
    database_url: str = Field(
        default="sqlite:///./thalos_prime.db",
        description="Database connection URL"
    )
    db_pool_size: int = Field(default=10, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, description="Max database connections overflow")
    
    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    
    # Cache settings
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    cache_max_size: int = Field(default=10000, description="Maximum cache size")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=60, description="Requests per minute")
    rate_limit_per_hour: int = Field(default=1000, description="Requests per hour")
    
    # Search settings
    default_search_mode: str = Field(default="hybrid", description="Default search mode")
    max_results_limit: int = Field(default=50, description="Maximum results per query")
    min_coherence_score: float = Field(default=0.0, description="Minimum coherence score")
    
    # Generation settings
    enable_local_generation: bool = Field(default=True, description="Enable local page generation")
    enable_remote_search: bool = Field(default=True, description="Enable remote Library search")
    
    # LLM settings
    llm_enabled: bool = Field(default=False, description="Enable LLM normalization")
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_api_key: Optional[str] = Field(default=None, description="LLM API key")
    llm_model: str = Field(default="gpt-3.5-turbo", description="LLM model name")
    llm_max_tokens: int = Field(default=500, description="Max tokens for LLM")
    
    # Security settings
    secret_key: str = Field(
        default="change-this-secret-key-in-production",
        description="Secret key for JWT"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    # CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins"
    )
    
    class Config:
        env_prefix = "THALOS_"
        case_sensitive = False


# Load configuration from environment
def load_config() -> APIConfig:
    """Load configuration from environment variables"""
    return APIConfig(
        host=os.getenv("THALOS_HOST", "0.0.0.0"),
        port=int(os.getenv("THALOS_PORT", "8000")),
        database_url=os.getenv("THALOS_DATABASE_URL", "sqlite:///./thalos_prime.db"),
        redis_url=os.getenv("THALOS_REDIS_URL", "redis://localhost:6379/0"),
        cache_ttl=int(os.getenv("THALOS_CACHE_TTL", "3600")),
        llm_enabled=os.getenv("THALOS_LLM_ENABLED", "false").lower() == "true",
        llm_provider=os.getenv("THALOS_LLM_PROVIDER", "openai"),
        llm_api_key=os.getenv("THALOS_LLM_API_KEY"),
        secret_key=os.getenv("THALOS_SECRET_KEY", "change-this-secret-key-in-production"),
    )


# Global configuration instance
config = load_config()
