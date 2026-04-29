"""Configuration management for ru-corrector service."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = Field(default="ru-corrector", description="Application name")
    HOST: str = Field(default="0.0.0.0", description="Host to bind to")
    PORT: int = Field(default=8000, description="Port to bind to")
    DEBUG: bool = Field(default=False, description="Enable debug mode")

    # Text processing limits
    MAX_TEXT_LEN: int = Field(default=15000, description="Maximum text length in characters")

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    # LanguageTool
    LT_URL: str = Field(
        default="https://api.languagetool.org", description="LanguageTool server URL"
    )
    LT_LANGUAGE: str = Field(
        default="ru-RU", description="LanguageTool language code"
    )

    # OpenAI refiner (optional)
    OPENAI_API_KEY: str | None = Field(default=None, description="OpenAI API key")
    ENABLE_OPENAI_REFINER: bool = Field(
        default=False, description="Enable optional OpenAI legal text refiner"
    )
    OPENAI_REFINER_MODEL: str = Field(
        default="gpt-4o-mini", description="OpenAI model for legal refiner"
    )
    OPENAI_REFINER_TEMPERATURE: float = Field(
        default=0.1, description="OpenAI legal refiner temperature"
    )

    # Correction options
    ENABLE_YO_REPLACEMENT: bool = Field(
        default=False, description="Enable ё replacement in corrections"
    )

    # Telegram bot (optional)
    TG_BOT_TOKEN: str | None = Field(default=None, description="Telegram bot token")
    
    # Legacy support
    BOT_TOKEN: str | None = Field(default=None, description="Legacy: Telegram bot token")
    DEFAULT_MODE: str = Field(default="legal", description="Default correction mode")


config = Config()
