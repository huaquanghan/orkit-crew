"""Configuration management with Pydantic Settings."""

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Planno Gateway
    plano_url: str = Field(default="http://localhost:8787", alias="PLANNO_URL")
    plano_api_key: Optional[str] = Field(default=None, alias="PLANNO_API_KEY")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    
    # Qdrant
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, alias="QDRANT_API_KEY")
    
    # App Settings
    app_env: AppEnv = Field(default=AppEnv.DEVELOPMENT, alias="APP_ENV")
    log_level: LogLevel = Field(default=LogLevel.INFO, alias="LOG_LEVEL")
    
    # CrewAI Settings
    crewai_memory_enabled: bool = Field(default=True, alias="CREWAI_MEMORY_ENABLED")
    crewai_cache_enabled: bool = Field(default=True, alias="CREWAI_CACHE_ENABLED")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == AppEnv.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == AppEnv.PRODUCTION


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
