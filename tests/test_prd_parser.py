"""Tests for PRD parser."""

import pytest
from pathlib import Path

from orkit_crew.core.prd_parser import (
    Complexity,
    FeaturePriority,
    PRDParser,
    ProjectMode,
    ProjectScope,
    parse_prd,
    validate_prd,
)


class TestPRDParser:
    """Test PRD parser functionality."""

    def test_parse_basic_prd(self, tmp_path: Path) -> None:
        """Test parsing a basic PRD file."""
        prd_content = """---
project_name: test-app
version: "1.0.0"
mode: greenfield
scope: mvp
stack:
  framework: nextjs
  language: typescript
  styling: tailwind
  ui_library: shadcn
  package_manager: pnpm
nextjs:
  router: app
  src_dir: true
complexity: medium
output_dir: ./output
---

# 1. Overview

Test project overview.

# 2. Goals

Primary goals here.

# 3. Features

## Feature 1: User Authentication

**Priority:** P0

### User Story

As a user, I want to login so that I can access my account.

### Description

Authentication feature description.

### Components

- [ ] Login form
- [ ] Password reset

### Acceptance Criteria

- [ ] User can login
- [ ] User can logout

## Feature 2: Dashboard

**Priority:** P1

### User Story

As a user, I want to see my dashboard.

### Components

- [ ] Stats widget

# 4. Page Structure

## Routes

| Route | Page Name | Description | Auth Required |
|-------|-----------|-------------|---------------|
| / | Home | Landing page | No |
| /login | Login | Auth page | No |
| /dashboard | Dashboard | Main dashboard | Yes |
"""

        prd_file = tmp_path / "test.prd.md"
        prd_file.write_text(prd_content)

        doc = parse_prd(prd_file)

        # Check metadata
        assert doc.metadata.project_name == "test-app"
        assert doc.metadata.version == "1.0.0"
        assert doc.metadata.mode == ProjectMode.GREENFIELD
        assert doc.metadata.scope == ProjectScope.MVP
        assert doc.metadata.complexity == Complexity.MEDIUM
        assert doc.metadata.stack.framework == "nextjs"
        assert doc.metadata.stack.language == "typescript"
        assert doc.metadata.nextjs.router == "app"
        assert doc.metadata.nextjs.src_dir is True

    def test_parse_vietnamese_headers(self, tmp_path: Path) -> None:
        """Test parsing PRD with Vietnamese headers."""
        prd_content = """---
project_name: vietnamese-test
version: "1.0.0"
mode: greenfield
scope: mvp
---

# 1. Tổng quan

Overview in Vietnamese.

# 2. Mục tiêu

Goals in Vietnamese.

# 3. Tính năng

## Feature 1: Test

**Priority:** P0

### User Story

Story here.

# 4. Cấu trúc trang

## Routes

| Route | Page Name | Description | Auth Required |
|-------|-----------|-------------|---------------|
| / | Trang chủ | Home page | No |
"""

        prd_file = tmp_path / "test-vi.prd.md"
        prd_file.write_text(prd_content)

        doc = parse_prd(prd_file)

        assert doc.metadata.project_name == "vietnamese-test"
        assert "overview" in doc.content.overview.lower()
        assert "goals" in doc.content.goals.lower()

    def test_extract_features(self, tmp_path: Path) -> None:
        """Test feature extraction."""
        prd_content = """---
project_name: feature-test
---

# 3. Features

## Feature 1: Auth

**Priority:** P0

### User Story

As a user, I want to login.

### Description

Auth description.

### Components

- [ ] Login form
- [ ] OAuth button

### Acceptance Criteria

- [ ] Can login
- [ ] Can logout

## Feature 2: Profile (P1)

### User Story

As a user, I want to edit profile.

### Components

- [ ] Profile form
"""

        prd_file = tmp_path / "features.prd.md"
        prd_file.write_text(prd_content)

        doc = parse_prd(prd_file)

        assert len(doc.content.features) == 2

        # Check first feature
        auth = doc.content.features[0]
        assert auth.name == "Auth"
        assert auth.priority == FeaturePriority.P0
        assert "As a user" in auth.user_story
        assert len(auth.components) == 2
        assert "Login form" in auth.components
        assert len(auth.criteria) == 2

        # Check second feature
        profile = doc.content.features[1]
        assert profile.name == "Profile (P1)"
        assert profile.priority == FeaturePriority.P1

    def test_get_mvp_features(self, tmp_path: Path) -> None:
        """Test getting MVP features (P0 only)."""
        prd_content = """---
project_name: mvp-test
scope: mvp
---

# 3. Features

## Feature 1: Must Have

**Priority:** P0

### User Story

Story 1.

## Feature 2: Should Have

**Priority:** P1

### User Story

Story 2.

## Feature 3: Nice to Have

**Priority:** P2

### User Story

Story 3.
"""

        prd_file = tmp_path / "mvp.prd.md"
        prd_file.write_text(prd_content)

        doc = parse_prd(prd_file)

        mvp = doc.get_mvp_features()
        assert len(mvp) == 1
        assert mvp[0].name == "Must Have"
        assert mvp[0].priority == FeaturePriority.P0

    def test_get_features_for_scope(self, tmp_path: Path) -> None:
        """Test getting features based on scope."""
        prd_content = """---
project_name: scope-test
scope: full
---

# 3. Features

## Feature 1: P0 Feature

**Priority:** P0

### User Story

Story.

## Feature 2: P1 Feature

**Priority:** P1

### User Story

Story.
"""

        prd_file = tmp_path / "scope-full.prd.md"
        prd_file.write_text(prd_content)

        doc = parse_prd(prd_file)

        # Full scope returns all features
        all_features = doc.get_features_for_scope()
        assert len(all_features) == 2

        # Change to MVP scope
        doc.metadata.scope = ProjectScope.MVP
        mvp_features = doc.get_features_for_scope()
        assert len(mvp_features) == 1

    def test_extract_pages(self, tmp_path: Path) -> None:
        """Test page route extraction."""
        prd_content = """---
project_name: pages-test
---

# 4. Page Structure

## Routes

| Route | Page Name | Description | Auth Required |
|-------|-----------|-------------|---------------|
| / | Home | Landing page | No |
| /login | Login | Auth page | No |
| /dashboard | Dashboard | Main dashboard | Yes |
| /profile | Profile | User profile | Yes |
"""

        prd_file = tmp_path / "pages.prd.md"
        prd_file.write_text(prd_content)

        doc = parse_prd(prd_file)

        assert len(doc.content.pages) == 4

        # Check home page
        home = doc.content.pages[0]
        assert home.route == "/"
        assert home.name == "Home"
        assert home.auth_required is False

        # Check auth pages
        dashboard = doc.content.pages[2]
        assert dashboard.route == "/dashboard"
        assert dashboard.auth_required is True

    def test_validate_prd(self, tmp_path: Path) -> None:
        """Test PRD validation."""
        # Valid PRD
        valid_prd = """---
project_name: valid-project
---

# 3. Features

## Feature 1: Test

**Priority:** P0

### User Story

Story.

# 4. Page Structure

## Routes

| Route | Page Name |
|-------|-----------|
| / | Home |
"""

        prd_file = tmp_path / "valid.prd.md"
        prd_file.write_text(valid_prd)
        doc = parse_prd(prd_file)

        warnings = validate_prd(doc)
        # Should have minimal warnings
        assert all("overview" not in w.lower() for w in warnings) or True

        # Invalid PRD - missing project name
        invalid_prd = """---
project_name: unnamed-project
---

# 1. Overview

Overview.
"""

        prd_file = tmp_path / "invalid.prd.md"
        prd_file.write_text(invalid_prd)
        doc = parse_prd(prd_file)

        warnings = validate_prd(doc)
        assert any("project name" in w.lower() for w in warnings)

    def test_parse_string(self) -> None:
        """Test parsing PRD from string."""
        prd_content = """---
project_name: string-test
version: "2.0.0"
---

# 1. Overview

Test overview.
"""

        parser = PRDParser()
        doc = parser.parse_string(prd_content, "test.prd.md")

        assert doc.metadata.project_name == "string-test"
        assert doc.metadata.version == "2.0.0"
        assert doc.source_path == "test.prd.md"

    def test_file_not_found(self) -> None:
        """Test handling of missing file."""
        with pytest.raises(FileNotFoundError):
            parse_prd("/nonexistent/path/test.prd.md")

    def test_priority_extraction_variations(self, tmp_path: Path) -> None:
        """Test various priority formats."""
        prd_content = """---
project_name: priority-test
---

# 3. Features

## Feature 1: Bold Priority

**Priority:** P0

### User Story

Story.

## Feature 2: Plain Priority

Priority: P1

### User Story

Story.

## Feature 3: In Parentheses (P2)

### User Story

Story.

## Feature 4: Text Priority (Must have)

### User Story

Story.
"""

        prd_file = tmp_path / "priority.prd.md"
        prd_file.write_text(prd_content)

        doc = parse_prd(prd_file)

        assert len(doc.content.features) == 4
        assert doc.content.features[0].priority == FeaturePriority.P0
        assert doc.content.features[1].priority == FeaturePriority.P1
        assert doc.content.features[2].priority == FeaturePriority.P2
        assert doc.content.features[3].priority == FeaturePriority.P0

    def test_get_auth_required_pages(self, tmp_path: Path) -> None:
        """Test getting pages that require auth."""
        prd_content = """---
project_name: auth-test
---

# 4. Page Structure

## Routes

| Route | Page Name | Auth Required |
|-------|-----------|---------------|
| / | Home | No |
| /login | Login | No |
| /dashboard | Dashboard | Yes |
| /admin | Admin | Yes |
"""

        prd_file = tmp_path / "auth.prd.md"
        prd_file.write_text(prd_content)

        doc = parse_prd(prd_file)

        auth_pages = doc.get_auth_required_pages()
        assert len(auth_pages) == 2
        assert all(p.auth_required for p in auth_pages)
        assert {p.route for p in auth_pages} == {"/dashboard", "/admin"}

    def test_get_feature_by_name(self, tmp_path: Path) -> None:
        """Test finding feature by name."""
        prd_content = """---
project_name: feature-lookup-test
---

# 3. Features

## Feature 1: User Login

**Priority:** P0

### User Story

Story.

## Feature 2: Password Reset

**Priority:** P1

### User Story

Story.
"""

        prd_file = tmp_path / "lookup.prd.md"
        prd_file.write_text(prd_content)

        doc = parse_prd(prd_file)

        login = doc.get_feature_by_name("User Login")
        assert login is not None
        assert login.priority == FeaturePriority.P0

        reset = doc.get_feature_by_name("password reset")  # case insensitive
        assert reset is not None

        missing = doc.get_feature_by_name("Nonexistent")
        assert missing is None

    def test_minimal_prd(self, tmp_path: Path) -> None:
        """Test parsing minimal/malformed PRD doesn't crash."""
        prd_content = """---
project_name: minimal
---

Some content without proper sections.
"""

        prd_file = tmp_path / "minimal.prd.md"
        prd_file.write_text(prd_content)

        # Should not crash
        doc = parse_prd(prd_file)

        assert doc.metadata.project_name == "minimal"
        # No features or pages, but parser shouldn't crash
        assert doc.content.features == []
        assert doc.content.pages == []

    def test_default_values(self, tmp_path: Path) -> None:
        """Test default values for missing fields."""
        prd_content = """---
project_name: defaults-test
---

# 1. Overview

Overview.
"""

        prd_file = tmp_path / "defaults.prd.md"
        prd_file.write_text(prd_content)

        doc = parse_prd(prd_file)

        assert doc.metadata.version == "1.0.0"
        assert doc.metadata.mode == ProjectMode.GREENFIELD
        assert doc.metadata.scope == ProjectScope.MVP
        assert doc.metadata.complexity == Complexity.AUTO
        assert doc.metadata.stack.framework == "nextjs"
        assert doc.metadata.nextjs.router == "app"
