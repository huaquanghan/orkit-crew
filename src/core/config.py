"""Configuration management for Changcomchien."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


@dataclass(frozen=True)
class Config:
    """Application configuration."""

    # Planno Gateway
    planno_api_url: str = "https://api.planno.io/v1"
    planno_api_key: str = ""

    # Models
    default_model: str = "gpt-4o-mini"
    fast_model: str = "gpt-4o-mini"
    deep_model: str = "gpt-4o"

    # Redis (optional)
    redis_url: str | None = None

    # Qdrant (optional)
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None

    # Logging
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            planno_api_url=os.getenv("PLANNO_API_URL", "https://api.planno.io/v1"),
            planno_api_key=os.getenv("PLANNO_API_KEY", ""),
            default_model=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            fast_model=os.getenv("FAST_MODEL", "gpt-4o-mini"),
            deep_model=os.getenv("DEEP_MODEL", "gpt-4o"),
            redis_url=os.getenv("REDIS_URL"),
            qdrant_url=os.getenv("QDRANT_URL"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def validate(self) -> None:
        """Validate configuration."""
        if not self.planno_api_key:
            raise ValueError("PLANNO_API_KEY is required")
