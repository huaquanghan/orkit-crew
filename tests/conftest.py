"""Pytest configuration and fixtures for Orkit Crew tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_prd_documents(fixtures_dir: Path) -> dict[str, Path]:
    """Return dictionary of sample PRD document paths."""
    return {
        "minimal": fixtures_dir / "prd_minimal.md",
        "medium": fixtures_dir / "prd_medium.md",
        "full": fixtures_dir / "prd_full.md",
        "extend": fixtures_dir / "prd_extend.md",
    }


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    mock = MagicMock()
    mock.chat = MagicMock()
    mock.chat_stream = MagicMock()
    mock.health_check = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_crewai_agent():
    """Create a mock CrewAI agent."""
    mock = MagicMock()
    mock.execute_sync = MagicMock()
    return mock


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear settings cache before each test."""
    from orkit_crew.core.config import clear_settings_cache
    clear_settings_cache()
    yield
