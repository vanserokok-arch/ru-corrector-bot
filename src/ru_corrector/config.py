"""Configuration management for ru-corrector service."""
import os
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Config:
    """Application configuration from environment variables."""

    # Application
    APP_NAME: str = os.getenv("APP_NAME", "ru-corrector")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Text processing limits
    MAX_TEXT_LEN: int = int(os.getenv("MAX_TEXT_LEN", "15000"))
    
    # Logging
    LOG_LEVEL: LogLevel = os.getenv("LOG_LEVEL", "INFO")  # type: ignore
    
    # LanguageTool
    LT_URL: str = os.getenv("LT_URL", "https://api.languagetool.org")
    
    # Telegram bot (optional, for backward compatibility)
    BOT_TOKEN: str | None = os.getenv("BOT_TOKEN")
    DEFAULT_MODE: str = os.getenv("DEFAULT_MODE", "min")


config = Config()
