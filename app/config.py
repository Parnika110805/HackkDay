import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    GEMINI_API_KEY: Optional[str] = None
    GEMMA_MODEL: str = "gemma-4-31b-it"
    SECRET_KEY: str = "urfeast_hackathon_secret_key_2026"
    DATABASE_URL: str = "sqlite:///urfeast.db"
    UPLOAD_DIR: str = "uploads"
    TTS_CACHE_DIR: str = "tts_cache"
    ENV: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure required directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.TTS_CACHE_DIR, exist_ok=True)
