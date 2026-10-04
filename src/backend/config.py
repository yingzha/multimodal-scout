"""
Configuration management.
All settings are read from environment variables.
"""

import os
from typing import List


class Config:
    """Configuration class for managing environment variables."""

    @property
    def database_url(self) -> str:
        """Get database URL."""
        return os.getenv(
            "DATABASE_URL",
            "postgresql://scout_user:scout_password@localhost:5432/multimodal_scout",
        )

    # --- LLM (any OpenAI-compatible API, Ollama by default) ---

    @property
    def llm_base_url(self) -> str:
        """Base URL of the OpenAI-compatible API. Set to empty to disable AI features."""
        return os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")

    @property
    def llm_api_key(self) -> str:
        """API key for the LLM server (Ollama ignores it)."""
        return os.getenv("LLM_API_KEY", "ollama")

    @property
    def llm_chat_model(self) -> str:
        """Model used for summaries, categorization and keyword suggestions."""
        return os.getenv("LLM_CHAT_MODEL", "gemma3:4b")

    @property
    def llm_embedding_model(self) -> str:
        """Model used for semantic search embeddings."""
        return os.getenv("LLM_EMBEDDING_MODEL", "bge-m3")

    @property
    def llm_timeout_seconds(self) -> float:
        """Timeout for a single LLM request."""
        return float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))

    @property
    def llm_max_concurrency(self) -> int:
        """Maximum number of summaries generated at the same time."""
        return max(1, int(os.getenv("LLM_MAX_CONCURRENCY", "2")))

    # --- Search ---
    # Cosine similarity cutoffs, measured for bge-m3. They depend on the embedding
    # model, so re-measure them with `python -m src.backend.cache_manager calibrate`
    # after changing it.

    @property
    def research_threshold(self) -> float:
        """Minimum similarity for a research paper to match a topic."""
        return float(os.getenv("RESEARCH_THRESHOLD", "0.52"))

    @property
    def industry_threshold(self) -> float:
        """Minimum similarity for industry content to match a topic."""
        return float(os.getenv("INDUSTRY_THRESHOLD", "0.52"))

    # --- Web ---

    @property
    def cors_origins(self) -> List[str]:
        """Origins allowed to call the API from a browser."""
        origins = os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        )
        return [origin.strip() for origin in origins.split(",") if origin.strip()]

    @property
    def local_user_email(self) -> str:
        """Email of the single local user that owns bookmarks and preferences."""
        return os.getenv("LOCAL_USER_EMAIL", "local@localhost")


# Global configuration instance
config = Config()
