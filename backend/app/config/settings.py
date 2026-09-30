"""
Centralized application configuration.

All configuration is loaded from environment variables (or a local .env file
during development). Nothing else in the application should read from
os.environ directly - everything goes through the `settings` singleton
exported from this module.
"""

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- LLM provider selection ------------------------------------------
    llm_provider: Literal["openai", "gemini"] = Field(default="openai", alias="LLM_PROVIDER")

    # --- OpenAI -----------------------------------------------------------
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: Optional[str] = Field(default=None, alias="OPENAI_BASE_URL")

    # --- Gemini (Google AI Studio) -----------------------------------------
    google_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    )
    gemini_model: str = Field(default="gemini-3.1-flash-lite", alias="GEMINI_MODEL")

    # --- Shared LLM settings -------------------------------------------------
    temperature: float = Field(default=0.0, alias="TEMPERATURE")
    llm_request_timeout: float = Field(default=60.0, alias="LLM_REQUEST_TIMEOUT")
    llm_max_retries: int = Field(default=2, alias="LLM_MAX_RETRIES")
    # Outbound throttle: max LLM calls per second across the whole process
    # (0 = unlimited). Useful for provider free-tier quotas.
    llm_requests_per_second: float = Field(default=0.0, alias="LLM_REQUESTS_PER_SECOND")

    # --- Chunking ---------------------------------------------------------
    chunk_size: int = Field(default=4000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=400, alias="CHUNK_OVERLAP")

    # --- Concurrency --------------------------------------------------------
    max_concurrency: int = Field(default=4, alias="MAX_CONCURRENCY")

    # --- Input validation ---------------------------------------------------
    min_article_words: int = Field(default=40, alias="MIN_ARTICLE_WORDS")
    max_article_chars: int = Field(default=200_000, alias="MAX_ARTICLE_CHARS")

    # --- URL loading ---------------------------------------------------------
    url_fetch_timeout: float = Field(default=10.0, alias="URL_FETCH_TIMEOUT")

    # --- API rate limiting (per client, inbound) -------------------------------
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=10, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    # Only enable behind a trusted reverse proxy that sets X-Forwarded-For.
    rate_limit_trust_proxy: bool = Field(default=False, alias="RATE_LIMIT_TRUST_PROXY")

    # --- Observability (optional) --------------------------------------------
    langsmith_api_key: Optional[str] = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_project: str = Field(default="ai-article-summarizer", alias="LANGSMITH_PROJECT")

    # --- API / CORS -----------------------------------------------------------
    cors_allow_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ALLOW_ORIGINS",
    )

    # --- Logging ---------------------------------------------------------------
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _normalize_provider(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_csv(cls, value):
        """Allow CORS_ALLOW_ORIGINS to be given as a comma-separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def validate(self) -> None:
        """
        Validate provider configuration.

        Raises ValueError with a clear message if the selected provider
        is missing required configuration.
        """
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "LLM_PROVIDER=openai requires OPENAI_API_KEY to be set."
            )
        if self.llm_provider == "gemini" and not self.google_api_key:
            raise ValueError(
                "LLM_PROVIDER=gemini requires GOOGLE_API_KEY to be set."
            )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once per process)."""
    return Settings()


# Convenience singleton used throughout the app.
settings = get_settings()
