"""Orkit Crew Configuration.

This module provides application settings with support for:
- Environment variables
- .env file loading
- Stack configuration alignment with PRD frontmatter schema
- Settings caching
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment.

    Priority order (highest to lowest):
    1. Environment variables
    2. .env file
    3. Default values

    Attributes:
        # LLM Configuration
        llm_base_url: Base URL for LLM API
        llm_api_key: API key for LLM service
        llm_model: Default LLM model to use
        llm_timeout: Request timeout in seconds
        llm_max_retries: Maximum number of retries

        # Application
        app_env: Application environment (development, production, testing)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

        # Stack Configuration (aligns with PRD frontmatter schema)
        default_framework: Default framework (nextjs)
        default_language: Default language (typescript)
        default_styling: Default styling approach (tailwind)
        default_ui_library: Default UI library (shadcn)
        default_package_manager: Default package manager (pnpm)
        default_nextjs_router: Default Next.js router (app)
        default_src_dir: Whether to use src directory by default (true)

        # Legacy aliases for backward compatibility
        planno_url: Legacy URL setting (maps to llm_base_url)
        planno_api_key: Legacy API key setting (maps to llm_api_key)
        default_model: Legacy model setting (maps to llm_model)
    """

    # LLM Configuration (new naming)
    llm_base_url: str = "http://localhost:8787"
    llm_api_key: str = ""
    llm_model: str = "gpt-5.4"
    llm_timeout: float = 120.0
    llm_max_retries: int = 3

    # Legacy aliases for backward compatibility
    planno_url: str = ""
    planno_api_key: str = ""
    default_model: str = ""

    # Application
    app_env: str = "development"
    log_level: str = "INFO"

    # Stack Configuration (aligns with PRD frontmatter schema)
    # These map to StackConfig in prd_parser.py
    default_framework: str = "nextjs"
    default_language: str = "typescript"
    default_styling: str = "tailwind"
    default_ui_library: str = "shadcn"
    default_package_manager: str = "pnpm"

    # Next.js specific defaults
    # These map to NextjsConfig in prd_parser.py
    default_nextjs_router: str = "app"
    default_src_dir: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to handle legacy settings.

        Maps legacy settings to new settings if new ones are not set.
        """
        # Map legacy planno_url to llm_base_url
        if not self.llm_base_url and self.planno_url:
            self.llm_base_url = self.planno_url
        elif self.planno_url and self.planno_url != "http://localhost:8787":
            # If planno_url is explicitly set (not default), use it
            self.llm_base_url = self.planno_url

        # Map legacy planno_api_key to llm_api_key
        if not self.llm_api_key and self.planno_api_key:
            self.llm_api_key = self.planno_api_key
        elif self.planno_api_key:
            self.llm_api_key = self.planno_api_key

        # Map legacy default_model to llm_model
        if not self.llm_model and self.default_model:
            self.llm_model = self.default_model
        elif self.default_model and self.default_model != "gpt-5.4":
            # If default_model is explicitly set, use it
            self.llm_model = self.default_model

    def get_stack_config(self) -> dict[str, str]:
        """Get stack configuration as dictionary.

        Returns:
            Dictionary matching StackConfig schema from prd_parser.
        """
        return {
            "framework": self.default_framework,
            "language": self.default_language,
            "styling": self.default_styling,
            "ui_library": self.default_ui_library,
            "package_manager": self.default_package_manager,
        }

    def get_nextjs_config(self) -> dict[str, str | bool]:
        """Get Next.js configuration as dictionary.

        Returns:
            Dictionary matching NextjsConfig schema from prd_parser.
        """
        return {
            "router": self.default_nextjs_router,
            "src_dir": self.default_src_dir,
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Cached Settings instance.
    """
    return Settings()


def clear_settings_cache() -> None:
    """Clear the settings cache.

    Useful for testing or when settings need to be reloaded.
    """
    get_settings.cache_clear()
