"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Configuration management for WAHOOPREDICT.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/wahoopredict"
    )
    
    # API
    api_secret: str = os.getenv("API_SECRET", "dev-secret-change-in-production")
    wahoo_base_url: str = os.getenv("WAHOO_BASE_URL", "https://api.wahoopredict.com")
    
    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

