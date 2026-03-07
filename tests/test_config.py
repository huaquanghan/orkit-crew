"""Tests for configuration."""

from __future__ import annotations

import os
from unittest import mock

import pytest

from orkit_crew.core.config import Settings, get_settings, clear_settings_cache


# Fixture to clear cache before each test
@pytest.fixture(autouse=True)
def clear_cache():
    """Clear settings cache before each test."""
    clear_settings_cache()
    yield


class TestDefaultSettings:
    """Test default settings values."""

    def test_default_llm_settings(self) -> None:
        """Test default LLM configuration."""
        settings = get_settings()

        assert settings.llm_base_url == "http://localhost:8787"
        assert settings.llm_api_key == ""
        assert settings.llm_model == "gpt-5.4"
        assert settings.llm_timeout == 120.0
        assert settings.llm_max_retries == 3

    def test_default_stack_settings(self) -> None:
        """Test default stack configuration."""
        settings = get_settings()

        assert settings.default_framework == "nextjs"
        assert settings.default_language == "typescript"
        assert settings.default_styling == "tailwind"
        assert settings.default_ui_library == "shadcn"
        assert settings.default_package_manager == "pnpm"

    def test_default_nextjs_settings(self) -> None:
        """Test default Next.js configuration."""
        settings = get_settings()

        assert settings.default_nextjs_router == "app"
        assert settings.default_src_dir is True

    def test_default_app_settings(self) -> None:
        """Test default application settings."""
        settings = get_settings()

        assert settings.app_env == "development"
        assert settings.log_level == "INFO"


class TestEnvironmentOverride:
    """Test environment variable overrides."""

    def test_override_llm_base_url(self) -> None:
        """Test overriding LLM base URL."""
        with mock.patch.dict(os.environ, {"LLM_BASE_URL": "https://api.example.com"}):
            clear_settings_cache()
            settings = get_settings()
            assert settings.llm_base_url == "https://api.example.com"

    def test_override_llm_api_key(self) -> None:
        """Test overriding LLM API key."""
        with mock.patch.dict(os.environ, {"LLM_API_KEY": "sk-test-key"}):
            clear_settings_cache()
            settings = get_settings()
            assert settings.llm_api_key == "sk-test-key"

    def test_override_llm_model(self) -> None:
        """Test overriding LLM model."""
        with mock.patch.dict(os.environ, {"LLM_MODEL": "gpt-4-turbo"}):
            clear_settings_cache()
            settings = get_settings()
            assert settings.llm_model == "gpt-4-turbo"

    def test_override_stack_config(self) -> None:
        """Test overriding stack configuration."""
        env_vars = {
            "DEFAULT_FRAMEWORK": "react",
            "DEFAULT_LANGUAGE": "javascript",
            "DEFAULT_STYLING": "css-modules",
            "DEFAULT_UI_LIBRARY": "mui",
            "DEFAULT_PACKAGE_MANAGER": "npm",
        }
        with mock.patch.dict(os.environ, env_vars):
            clear_settings_cache()
            settings = get_settings()
            assert settings.default_framework == "react"
            assert settings.default_language == "javascript"
            assert settings.default_styling == "css-modules"
            assert settings.default_ui_library == "mui"
            assert settings.default_package_manager == "npm"

    def test_override_nextjs_config(self) -> None:
        """Test overriding Next.js configuration."""
        env_vars = {
            "DEFAULT_NEXTJS_ROUTER": "pages",
            "DEFAULT_SRC_DIR": "false",
        }
        with mock.patch.dict(os.environ, env_vars):
            clear_settings_cache()
            settings = get_settings()
            assert settings.default_nextjs_router == "pages"
            assert settings.default_src_dir is False


class TestLegacyCompatibility:
    """Test backward compatibility with legacy settings."""

    def test_legacy_planno_url_maps_to_llm_base_url(self) -> None:
        """Test that legacy planno_url maps to llm_base_url."""
        with mock.patch.dict(os.environ, {"PLANNO_URL": "https://legacy.example.com"}):
            clear_settings_cache()
            settings = get_settings()
            assert settings.llm_base_url == "https://legacy.example.com"

    def test_legacy_planno_api_key_maps_to_llm_api_key(self) -> None:
        """Test that legacy planno_api_key maps to llm_api_key."""
        with mock.patch.dict(os.environ, {"PLANNO_API_KEY": "legacy-key"}):
            clear_settings_cache()
            settings = get_settings()
            assert settings.llm_api_key == "legacy-key"

    def test_legacy_default_model_maps_to_llm_model(self) -> None:
        """Test that legacy default_model maps to llm_model."""
        with mock.patch.dict(os.environ, {"DEFAULT_MODEL": "legacy-model"}):
            clear_settings_cache()
            settings = get_settings()
            assert settings.llm_model == "legacy-model"

    def test_new_settings_take_precedence_over_legacy(self) -> None:
        """Test that new settings take precedence over legacy."""
        env_vars = {
            "LLM_BASE_URL": "https://new.example.com",
            "PLANNO_URL": "https://legacy.example.com",
        }
        with mock.patch.dict(os.environ, env_vars):
            clear_settings_cache()
            settings = get_settings()
            assert settings.llm_base_url == "https://new.example.com"


class TestStackConfigMethods:
    """Test stack configuration helper methods."""

    def test_get_stack_config(self) -> None:
        """Test get_stack_config method."""
        settings = get_settings()
        stack = settings.get_stack_config()

        assert isinstance(stack, dict)
        assert stack["framework"] == "nextjs"
        assert stack["language"] == "typescript"
        assert stack["styling"] == "tailwind"
        assert stack["ui_library"] == "shadcn"
        assert stack["package_manager"] == "pnpm"

    def test_get_nextjs_config(self) -> None:
        """Test get_nextjs_config method."""
        settings = get_settings()
        nextjs = settings.get_nextjs_config()

        assert isinstance(nextjs, dict)
        assert nextjs["router"] == "app"
        assert nextjs["src_dir"] is True

    def test_stack_config_matches_prd_schema(self) -> None:
        """Test that stack config matches PRD parser StackConfig schema."""
        from orkit_crew.core.prd_parser import StackConfig

        settings = get_settings()
        stack_dict = settings.get_stack_config()

        # Should be able to create StackConfig from settings
        stack = StackConfig(**stack_dict)
        assert stack.framework == settings.default_framework


class TestSettingsCaching:
    """Test settings caching behavior."""

    def test_settings_are_cached(self) -> None:
        """Test that settings are cached."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be same object due to caching
        assert settings1 is settings2

    def test_clear_cache_creates_new_instance(self) -> None:
        """Test that clearing cache creates new instance."""
        settings1 = get_settings()
        clear_settings_cache()
        settings2 = get_settings()

        # Should be different objects
        assert settings1 is not settings2

    def test_clear_cache_allows_new_values(self) -> None:
        """Test that clearing cache allows new env values to be read."""
        # Get initial settings
        settings1 = get_settings()
        initial_model = settings1.llm_model

        # Change environment
        with mock.patch.dict(os.environ, {"LLM_MODEL": "different-model"}):
            clear_settings_cache()
            settings2 = get_settings()

            # Should have new value
            assert settings2.llm_model == "different-model"
            assert settings2.llm_model != initial_model
