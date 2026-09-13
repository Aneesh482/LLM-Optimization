"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration. Values come from .env or the OS environment."""

    # --- Gemini ---
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    default_model: str = Field(default="gemini-3.6-flash", description="Default Gemini model")

    # --- App ---
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=False)
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)

    # --- Database ---
    database_url: str = Field(default="sqlite+aiosqlite:///./llm_gateway.db")

    # --- Rate limiting ---
    rate_limit_rpm: int = Field(default=60, description="Requests per minute")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# Model-specific pricing (USD per 1 million tokens)
# Source: https://ai.google.dev/pricing (as of 2026)
MODEL_PRICING = {
    "gemini-3.6-flash": {
        "input_per_million": 0.075,
        "output_per_million": 0.30,
    },
    "gemini-2.5-flash": {
        "input_per_million": 0.075,
        "output_per_million": 0.30,
    },
    "gemini-2.5-pro": {
        "input_per_million": 1.25,
        "output_per_million": 5.00,
    },
    # Fallback for unknown models
    "default": {
        "input_per_million": 0.075,
        "output_per_million": 0.30,
    },
}


# Singleton — import this everywhere.
settings = Settings()
