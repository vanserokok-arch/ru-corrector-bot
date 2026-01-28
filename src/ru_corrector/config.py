"""Configuration management for ru-corrector service."""

import os
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class Config:
    """Application configuration from environment variables."""

    # Application
    APP_NAME: str = os.getenv("APP_NAME", "ru-corrector")
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # PORT with validation
    _port_str = os.getenv("PORT", "8000")
    try:
        PORT: int = int(_port_str)
    except ValueError:
        raise ValueError(f"PORT must be a valid integer, got: {_port_str}") from None

    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Text processing limits with validation
    _max_len_str = os.getenv("MAX_TEXT_LEN", "15000")
    try:
        MAX_TEXT_LEN: int = int(_max_len_str)
    except ValueError:
        raise ValueError(f"MAX_TEXT_LEN must be a valid integer, got: {_max_len_str}") from None

    # Logging with validation
    _log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    if _log_level_str not in VALID_LOG_LEVELS:
        raise ValueError(f"LOG_LEVEL must be one of {VALID_LOG_LEVELS}, got: {_log_level_str}")
    LOG_LEVEL: LogLevel = _log_level_str  # type: ignore

    # LanguageTool
    LT_URL: str = os.getenv("LT_URL", "https://api.languagetool.org")

    # Telegram bot (optional, for backward compatibility)
    BOT_TOKEN: str | None = os.getenv("BOT_TOKEN")
    DEFAULT_MODE: str = os.getenv("DEFAULT_MODE", "min")


config = Config()
