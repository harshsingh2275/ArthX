from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path
import os

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DATABASE_URL: str = f"sqlite:///{ROOT_DIR / 'data' / 'arthx.db'}"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    GEMINI_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gemini-1.5-flash"
    EXPLAINABILITY_MODE: str = "auto"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())

    model_config = SettingsConfigDict(
        env_file=[
            str(BACKEND_DIR / ".env"),
            str(ROOT_DIR / ".env"),
        ],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
