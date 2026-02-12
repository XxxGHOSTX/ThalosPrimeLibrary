"""Configuration management for Thalos Prime."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Settings
    api_key: Optional[str] = Field(default=None, description="Optional API key for authentication")
    enable_api_key_auth: bool = Field(default=False, description="Enable API key authentication")

    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # Seed Policy
    seed_salt: str = Field(default="thalos_prime_default_salt", description="Salt for seed generation")
    time_bucket_seconds: int = Field(default=3600, description="Time bucket for seed generation")

    # Rate Limiting
    max_requests_per_minute: int = Field(default=60, description="Maximum requests per minute")

    # Corpus and Index
    corpus_dir: str = Field(default="corpus", description="Corpus directory")
    index_path: str = Field(default="data/tfidf_index.pkl", description="TF-IDF index path")
    manifest_path: str = Field(default="data/manifest.json", description="Corpus manifest path")

    # State Store
    state_db_path: str = Field(default="data/state.db", description="SQLite database path")

    # Event Log
    event_log_path: str = Field(default="data/events.jsonl", description="Event log path")

    # Checkpoint
    checkpoint_dir: str = Field(default="data/checkpoints", description="Checkpoint directory")

    # Generation Parameters
    max_sentences: int = Field(default=5, description="Maximum sentences in generation")
    top_k_retrieval: int = Field(default=3, description="Top K documents to retrieve")

    def get_corpus_path(self) -> Path:
        """Get corpus directory path."""
        return Path(self.corpus_dir)

    def get_index_path(self) -> Path:
        """Get index file path."""
        return Path(self.index_path)

    def get_manifest_path(self) -> Path:
        """Get manifest file path."""
        return Path(self.manifest_path)

    def get_state_db_path(self) -> Path:
        """Get state database path."""
        return Path(self.state_db_path)

    def get_event_log_path(self) -> Path:
        """Get event log path."""
        return Path(self.event_log_path)

    def get_checkpoint_dir(self) -> Path:
        """Get checkpoint directory path."""
        return Path(self.checkpoint_dir)

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.get_corpus_path().mkdir(parents=True, exist_ok=True)
        self.get_index_path().parent.mkdir(parents=True, exist_ok=True)
        self.get_manifest_path().parent.mkdir(parents=True, exist_ok=True)
        self.get_state_db_path().parent.mkdir(parents=True, exist_ok=True)
        self.get_event_log_path().parent.mkdir(parents=True, exist_ok=True)
        self.get_checkpoint_dir().mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
