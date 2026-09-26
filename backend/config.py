from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DATABASE_URL: str = f"sqlite:///{ROOT_DIR / 'data' / 'arthx.db'}"
    CORS_ALLOWED_ORIGINS: str = "*"
    # LLM provider — Groq (replaces Gemini)
    GROQ_API_KEY: str = ""
    LLM_MODEL_NAME: str = "openai/gpt-oss-120b"
    EXPLAINABILITY_MODE: str = "auto"  # "auto" | "template"

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ALLOWED_ORIGINS or self.CORS_ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def has_llm_key(self) -> bool:
        """True when a Groq API key is present and non-empty."""
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())

    # Keep legacy alias so any existing code referencing has_gemini_key still works
    @property
    def has_gemini_key(self) -> bool:
        return self.has_llm_key

    model_config = SettingsConfigDict(
        env_file=[
            str(BACKEND_DIR / ".env"),
            str(ROOT_DIR / ".env"),
        ],
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
