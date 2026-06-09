"""Application configuration (SRS Appendix A — Environment Variables).

Settings are read from environment variables / a local ``.env`` file. Every
external-service key is optional: when a key is absent the corresponding client
runs in deterministic *mock* mode so the entire pipeline still works offline.
"""
from __future__ import annotations

from functools import lru_cache

try:  # pydantic-settings is the canonical source
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _HAS_PYDANTIC_SETTINGS = True
except Exception:  # pragma: no cover - fallback if dependency missing
    _HAS_PYDANTIC_SETTINGS = False


if _HAS_PYDANTIC_SETTINGS:

    class Settings(BaseSettings):
        """Strongly-typed application settings."""

        model_config = SettingsConfigDict(
            env_file=".env", env_file_encoding="utf-8", extra="ignore"
        )

        # --- Credentials ---
        openai_api_key: str = ""
        anthropic_api_key: str = ""

        # --- LLM provider / models ---
        # provider: "auto" picks OpenAI when OPENAI_API_KEY is set, else Anthropic.
        llm_provider: str = "auto"  # auto | openai | anthropic
        openai_chat_model: str = "gpt-4o-mini"
        anthropic_model: str = "claude-sonnet-4-6"
        embedding_model: str = "text-embedding-3-small"

        # --- Infrastructure ---
        vector_store: str = "faiss"  # faiss | chroma | memory
        mcp_server_port: int = 8001
        api_port: int = 8000

        # --- Observability ---
        langchain_tracing_v2: bool = False
        langchain_api_key: str = ""

        # --- Limits / tuning ---
        max_upload_mb: int = 50
        # Floor separating relevant chunks from noise. The SRS's nominal 0.75 is
        # unrealistic for text-embedding-3-small query→passage cosine (~0.2–0.5),
        # so the working default is 0.2; raise it for stricter retrieval.
        similarity_threshold: float = 0.2

        # --- Auth (SRS 4.4: OAuth 2.0 JWT) ---
        jwt_secret: str = "dev-insecure-change-me"
        jwt_algorithm: str = "HS256"
        jwt_expire_minutes: int = 60 * 24  # 24 hours
        auth_db_path: str = ".data/users.db"

        @property
        def has_anthropic(self) -> bool:
            return bool(self.anthropic_api_key)

        @property
        def has_openai(self) -> bool:
            return bool(self.openai_api_key)

        @property
        def resolved_provider(self) -> str:
            """Concrete LLM provider after applying the 'auto' rule."""
            if self.llm_provider != "auto":
                return self.llm_provider
            if self.has_openai:
                return "openai"
            if self.has_anthropic:
                return "anthropic"
            return "none"

else:  # pragma: no cover - minimal fallback

    import os

    class Settings:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
            self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
            self.llm_provider = os.getenv("LLM_PROVIDER", "auto")
            self.openai_chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
            self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
            self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
            self.vector_store = os.getenv("VECTOR_STORE", "faiss")
            self.mcp_server_port = int(os.getenv("MCP_SERVER_PORT", "8001"))
            self.api_port = int(os.getenv("API_PORT", "8000"))
            self.langchain_tracing_v2 = os.getenv("LANGCHAIN_TRACING_V2", "false") == "true"
            self.langchain_api_key = os.getenv("LANGCHAIN_API_KEY", "")
            self.max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "50"))
            self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.2"))
            self.jwt_secret = os.getenv("JWT_SECRET", "dev-insecure-change-me")
            self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
            self.jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", str(60 * 24)))
            self.auth_db_path = os.getenv("AUTH_DB_PATH", ".data/users.db")

        @property
        def has_anthropic(self) -> bool:
            return bool(self.anthropic_api_key)

        @property
        def has_openai(self) -> bool:
            return bool(self.openai_api_key)

        @property
        def resolved_provider(self) -> str:
            if self.llm_provider != "auto":
                return self.llm_provider
            if self.has_openai:
                return "openai"
            if self.has_anthropic:
                return "anthropic"
            return "none"


@lru_cache
def get_settings() -> "Settings":
    """Return a cached singleton ``Settings`` instance."""
    return Settings()
