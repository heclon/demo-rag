"""
Centralized application configuration.

All environment-driven settings live here so the rest of the codebase never
reads `os.environ` directly. Every value has a working local default matching
docker-compose.yml, so the API boots with no .env file at all.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "demo-rag-api"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

    # --- PostgreSQL ---
    database_url: str = Field(
        default="postgresql+psycopg://demo:demo@localhost:5432/demo_rag",
        description="SQLAlchemy DSN. Defaults to the docker-compose postgres service.",
    )

    # --- OpenSearch ---
    opensearch_endpoint: str = "https://localhost:9200"
    opensearch_index: str = "product_reviews"
    opensearch_user: str = "admin"
    # Matches docker-compose.yml; local demo only. OpenSearch rejects any
    # password containing "admin" as too similar to the user name.
    opensearch_password: str = "Vect0r@Se4rch-2026"
    opensearch_verify_certs: bool = False  # local OpenSearch uses a self-signed cert

    # --- LLM (Text-to-SQL, agent routing, answer synthesis) ---
    llm_provider: Literal["mock", "anthropic"] = "mock"
    """
    'mock' is the default so the demo runs offline with zero API keys — it uses
    deterministic rule-based stand-ins for SQL generation, agent routing, and
    answer synthesis. Set ANTHROPIC_API_KEY and llm_provider=anthropic to use a
    real Claude model. See docs/decisions.md.
    """
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5"
    anthropic_max_tokens: int = 2048

    # --- Embeddings (pgvector semantic search) ---
    embedding_provider: Literal["local", "voyage"] = "local"
    """
    'local' is a dependency-free hashing vectorizer — real lexical retrieval
    that runs offline. 'voyage' calls Voyage AI for true dense embeddings when
    VOYAGE_API_KEY is set. Both write to the same pgvector column.
    """
    voyage_api_key: str | None = None
    voyage_model: str = "voyage-3.5-lite"
    embedding_dimensions: int = 1024

    # --- Agent ---
    agent_max_tool_calls: int = 3

    # --- Data ---
    seed_data_path: str | None = None
    """Absolute path to products.json. Defaults to <repo-root>/data/products.json
    when unset; the container image sets it to /data/products.json."""

    @property
    def sqlalchemy_url(self) -> str:
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
