"""Tests for PRD parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from orkit_crew.core.prd_parser import (
    PRDDocument,
    PRDParser,
    FeaturePriority,
    ProjectMode,
    ProjectScope,
    Complexity,
    StackConfig,
    NextjsConfig,
    parse_prd,
    validate_prd,
)


# Fixtures
@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def minimal_prd(fixtures_dir: Path) -> PRDDocument:
    """Load minimal PRD fixture."""
    return parse_prd(fixtures_dir / "prd_minimal.md")


@pytest.fixture
def medium_prd(fixtures_dir: Path) -> PRDDocument:
    """Load medium PRD fixture."""
    return parse_prd(fixtures_dir / "prd_medium.md")


@pytest.fixture
def full_prd(fixtures_dir: Path) -> PRDDocument:
    """Load full PRD fixture."""
    return parse_prd(fixtures_dir / "prd_full.md")


@pytest.fixture
def extend_prd(fixtures_dir: Path) -> PRDDocument:
    """Load extend mode PRD fixture."""
    return parse_prd(fixtures_dir / "prd_extend.md")


# Test frontmatter parsing
class TestFrontmatterParsing:
    """Test YAML frontmatter parsing."""

    def test_minimal_prd_metadata(self, minimal_prd: PRDDocument) -> None:
        """Test minimal PRD metadata parsing."""
        assert minimal_prd.metadata.project_name == "minimal-landing-page"
        assert minimal_prd.metadata.version == "1.0.0"
        assert minimal_prd.metadata.mode == ProjectMode.GREENFIELD
        assert minimal_prd.metadata.scope == ProjectScope.MVP
        assert minimal_prd.metadata.complexity == Complexity.LOW

    def test_medium_prd_metadata(self, medium_prd: PRDDocument) -> None:
        """Test medium PRD metadata parsing."""
        assert medium_prd.metadata.project_name == "dashboard-app"
        assert medium_prd.metadata.mode == ProjectMode.GREENFIELD
        assert medium_prd.metadata.scope == ProjectScope.MVP

    def test_extend_prd_metadata(self, extend_prd: PRDDocument) -> None:
        """Test extend mode PRD metadata parsing."""
        assert extend_prd.metadata.mode == ProjectMode.EXTEND
        assert extend_prd.metadata.project_name == "existing-ecommerce"

    def test_full_prd_metadata(self, full_prd: PRDDocument) -> None:
        """Test full PRD metadata parsing."""
        assert full_prd.metadata.project_name == "enterprise-crm"
        assert full_prd.metadata.scope == ProjectScope.FULL
        assert full_prd.metadata.complexity == Complexity.HIGH

    def test_stack_config(self, medium_prd: PRDDocument) -> None:
        """Test stack configuration parsing."""
        stack = medium_prd.metadata.stack
        assert isinstance(stack, StackConfig)
        assert stack.framework == "nextjs"
        assert stack.language == "typescript"
        assert stack.styling == "tailwind"
        assert stack.ui_library == "shadcn"
        assert stack.package_manager == "pnpm"

    def test_nextjs_config(self, medium_prd: PRDDocument) -> None:
        """Test Next.js configuration parsing."""
        nextjs = medium_prd.metadata.nextjs
        assert isinstance(nextjs, NextjsConfig)
        assert nextjs.router == "app"
        assert nextjs.src_dir is True


# Test body section extraction
class TestBodySectionExtraction:
    """Test markdown body section extraction."""

    def test_overview_extraction(self, minimal_prd: PRDDocument) -> None:
        """Test overview section extraction."""
        assert "landing page" in minimal_prd.content.overview.lower()

    def test_goals_extraction(self, minimal_prd: PRDDocument) -> None:
        """Test goals section extraction."""
        assert minimal_prd.content.goals
        assert "professional" in minimal_prd.content.goals.lower()

    def test_features_extraction(self, minimal_prd: PRDDocument) -> None:
        """Test features section extraction."""
        assert len(minimal_prd.content.features) > 0
        feature = minimal_prd.content.features[0]
        assert feature.name == "Hero Section"
        assert feature.priority == FeaturePriority.P0

    def test_pages_extraction(self, medium_prd: PRDDocument) -> None:
        """Test pages section extraction."""
        assert len(medium_prd.content.pages) > 0
        # Should have multiple pages including dashboard
        page_routes = [p.route for p in medium_prd.content.pages]
        assert "/" in page_routes
        assert "/dashboard" in page_routes

    def test_auth_pages(self, medium_prd: PRDDocument) -> None:
        """Test auth required flag extraction."""
        dashboard_page = next(
            (p for p in medium_prd.content.pages if p.route == "/dashboard"),
            None
        )
        assert dashboard_page is not None
        assert dashboard_page.auth_required is True


# Test feature extraction with priorities
class TestFeatureExtraction:
    """Test feature extraction with priorities."""

    def test_p0_features(self, medium_prd: PRDDocument) -> None:
        """Test P0 (must-have) feature extraction."""
        p0_features = medium_prd.get_mvp_features()
        assert len(p0_features) >= 2
        for feature in p0_features:
            assert feature.priority == FeaturePriority.P0

    def test_p1_features(self, medium_prd: PRDDocument) -> None:
        """Test P1 (should-have) feature extraction."""
        p1_features = [
            f for f in medium_prd.content.features
            if f.priority == FeaturePriority.P1
        ]
        assert len(p1_features) >= 2

    def test_feature_components(self, minimal_prd: PRDDocument) -> None:
        """Test feature component checklist extraction."""
        feature = minimal_prd.content.features[0]
        assert len(feature.components) > 0
        assert "Hero title" in feature.components

    def test_feature_criteria(self, minimal_prd: PRDDocument) -> None:
        """Test feature acceptance criteria extraction."""
        feature = minimal_prd.content.features[0]
        assert len(feature.criteria) > 0
        assert any("Hero" in c for c in feature.criteria)

    def test_get_feature_by_name(self, medium_prd: PRDDocument) -> None:
        """Test finding feature by name."""
        feature = medium_prd.get_feature_by_name("User Authentication")
        assert feature is not None
        assert feature.priority == FeaturePriority.P0

    def test_get_features_for_scope(self, medium_prd: PRDDocument) -> None:
        """Test getting features based on scope."""
        # MVP scope should return only P0 features
        mvp_features = medium_prd.get_features_for_scope()
        assert all(f.priority == FeaturePriority.P0 for f in mvp_features)


# Test validation warnings
class TestValidation:
    """Test PRD validation."""

    def test_minimal_prd_validation(self, minimal_prd: PRDDocument) -> None:
        """Test minimal PRD validation."""
        warnings = validate_prd(minimal_prd)
        # Minimal PRD should have no critical warnings
        assert isinstance(warnings, list)

    def test_missing_frontmatter_defaults(self) -> None:
        """Test PRD with missing frontmatter uses defaults."""
        content = """# Project

## Overview
Test project.

## Features

### Feature 1
Description here.
"""
        parser = PRDParser()
        doc = parser.parse_string(content)

        # Should use defaults
        assert doc.metadata.project_name == "unnamed-project"
        assert doc.metadata.version == "1.0.0"
        assert doc.metadata.mode == ProjectMode.GREENFIELD

    def test_no_features_warning(self) -> None:
        """Test warning for PRD without features."""
        content = """---
project_name: test
---

# Overview
Test.
"""
        parser = PRDParser()
        doc = parser.parse_string(content)
        warnings = validate_prd(doc)

        assert any("No features" in w for w in warnings)

    def test_no_p0_features_warning(self) -> None:
        """Test warning for PRD without P0 features."""
        content = """---
project_name: test
---

# Features

## Feature 1
**Priority:** P1

Description.
"""
        parser = PRDParser()
        doc = parser.parse_string(content)
        warnings = validate_prd(doc)

        assert any("No P0" in w for w in warnings)


# Test edge cases
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_content(self) -> None:
        """Test parsing empty content."""
        parser = PRDParser()
        doc = parser.parse_string("")
        assert doc.metadata.project_name == "unnamed-project"

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test file not found error."""
        with pytest.raises(FileNotFoundError):
            parse_prd(tmp_path / "nonexistent.md")

    def test_vietnamese_headers(self) -> None:
        """Test Vietnamese header recognition."""
        content = """---
project_name: test
---

# 1. Tổng Quan

Vietnamese content.

# 2. Mục Tiêu

Goals here.
"""
        parser = PRDParser()
        doc = parser.parse_string(content)
        assert "Vietnamese content" in doc.content.overview
        assert "Goals" in doc.content.goals

    def test_complexity_levels(self) -> None:
        """Test all complexity levels."""
        for level in ["auto", "low", "medium", "high"]:
            content = f"""---
project_name: test
complexity: {level}
---

# Overview
Test.
"""
            parser = PRDParser()
            doc = parser.parse_string(content)
            assert doc.metadata.complexity.value == level

    def test_get_auth_required_pages(self, medium_prd: PRDDocument) -> None:
        """Test getting pages that require auth."""
        auth_pages = medium_prd.get_auth_required_pages()
        assert len(auth_pages) > 0
        for page in auth_pages:
            assert page.auth_required is True
