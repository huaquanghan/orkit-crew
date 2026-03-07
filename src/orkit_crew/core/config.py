"""Orkit Crew Configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Planno LLM Gateway
    planno_url: str = "http://localhost:8787"
    planno_api_key: str = ""

    # Default model
    default_model: str = "gpt-5.4"

    # Application
    app_env: str = "development"
    log_level: str = "INFO"

    # Pipeline defaults
    default_framework: str = "nextjs"
    default_language: str = "typescript"
    default_styling: str = "tailwindcss"
    default_ui_library: str = "shadcn"
    default_package_manager: str = "pnpm"
    default_nextjs_router: str = "app"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
