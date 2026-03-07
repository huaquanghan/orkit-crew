"""PRD Parser - Parse PRD documents with YAML frontmatter.

This module provides parsing capabilities for PRD (Project Requirements Document)
files with YAML frontmatter and markdown content sections.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any

import frontmatter
from pydantic import BaseModel, Field, field_validator


class ProjectMode(str, Enum):
    """Project mode: greenfield or extend existing."""

    GREENFIELD = "greenfield"
    EXTEND = "extend"


class ProjectScope(str, Enum):
    """Project scope: mvp or full implementation."""

    MVP = "mvp"
    FULL = "full"


class Complexity(str, Enum):
    """Project complexity level."""

    AUTO = "auto"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FeaturePriority(str, Enum):
    """Feature priority levels."""

    P0 = "P0"  # Must have
    P1 = "P1"  # Should have
    P2 = "P2"  # Nice to have


class StackConfig(BaseModel):
    """Technology stack configuration."""

    framework: str = "nextjs"
    language: str = "typescript"
    styling: str = "tailwind"
    ui_library: str = "shadcn"
    package_manager: str = "pnpm"


class NextjsConfig(BaseModel):
    """Next.js specific configuration."""

    router: str = "app"  # "app" or "pages"
    src_dir: bool = True


class Feature(BaseModel):
    """A single feature requirement."""

    name: str
    priority: FeaturePriority = FeaturePriority.P1
    description: str = ""
    user_story: str = ""
    components: list[str] = Field(default_factory=list)
    criteria: list[str] = Field(default_factory=list)


class PageRoute(BaseModel):
    """A page route definition."""

    route: str
    name: str
    description: str = ""
    auth_required: bool = False


class PRDMetadata(BaseModel):
    """PRD YAML frontmatter metadata."""

    project_name: str
    version: str = "1.0.0"
    mode: ProjectMode = ProjectMode.GREENFIELD
    scope: ProjectScope = ProjectScope.MVP
    stack: StackConfig = Field(default_factory=StackConfig)
    nextjs: NextjsConfig = Field(default_factory=NextjsConfig)
    complexity: Complexity = Complexity.AUTO
    output_dir: str = "./output"

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator("scope", mode="before")
    @classmethod
    def validate_scope(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator("complexity", mode="before")
    @classmethod
    def validate_complexity(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.lower()
        return v


class PRDContent(BaseModel):
    """Parsed PRD content sections."""

    overview: str = ""
    goals: str = ""
    features: list[Feature] = Field(default_factory=list)
    pages: list[PageRoute] = Field(default_factory=list)
    api_requirements: str = ""
    database_schema: str = ""
    auth_requirements: str = ""
    ui_guidelines: str = ""
    performance_requirements: str = ""
    security_considerations: str = ""
    deployment: str = ""
    timeline: str = ""
    raw_sections: dict[str, str] = Field(default_factory=dict)


class PRDDocument(BaseModel):
    """Complete parsed PRD document."""

    metadata: PRDMetadata
    content: PRDContent
    source_path: str | None = None

    def get_mvp_features(self) -> list[Feature]:
        """Get only P0 (must-have) features."""
        return [f for f in self.content.features if f.priority == FeaturePriority.P0]

    def get_features_for_scope(self) -> list[Feature]:
        """Get features based on project scope setting."""
        if self.metadata.scope == ProjectScope.MVP:
            return self.get_mvp_features()
        return self.content.features

    def get_feature_by_name(self, name: str) -> Feature | None:
        """Find a feature by name (case-insensitive)."""
        name_lower = name.lower()
        for feature in self.content.features:
            if feature.name.lower() == name_lower:
                return feature
        return None

    def get_auth_required_pages(self) -> list[PageRoute]:
        """Get pages that require authentication."""
        return [p for p in self.content.pages if p.auth_required]


class PRDParser:
    """Parser for PRD documents with YAML frontmatter."""

    # Section header mappings (Vietnamese and English)
    SECTION_HEADERS: dict[str, list[str]] = {
        "overview": [
            "1. tổng quan",
            "1. overview",
            "tổng quan",
            "overview",
        ],
        "goals": [
            "2. mục tiêu",
            "2. goals",
            "mục tiêu",
            "goals",
            "objectives",
        ],
        "features": [
            "3. tính năng",
            "3. features",
            "tính năng",
            "features",
            "functional requirements",
        ],
        "pages": [
            "4. cấu trúc trang",
            "4. page structure",
            "cấu trúc trang",
            "page structure",
            "routes",
            "navigation",
        ],
        "api_requirements": [
            "5. api requirements",
            "api",
            "endpoints",
        ],
        "database_schema": [
            "6. database schema",
            "database",
            "schema",
            "data model",
        ],
        "auth_requirements": [
            "7. authentication",
            "7. auth",
            "7. authorization",
            "authentication",
            "authorization",
        ],
        "ui_guidelines": [
            "8. ui/ux",
            "8. ui guidelines",
            "ui/ux",
            "ui guidelines",
            "design system",
        ],
        "performance_requirements": [
            "9. performance",
            "performance requirements",
        ],
        "security_considerations": [
            "10. security",
            "security considerations",
        ],
        "deployment": [
            "11. deployment",
            "deployment",
            "build",
        ],
        "timeline": [
            "12. timeline",
            "timeline",
            "schedule",
            "phases",
        ],
    }

    def __init__(self) -> None:
        """Initialize the parser."""
        self.warnings: list[str] = []

    def parse_file(self, file_path: str | Path) -> PRDDocument:
        """Parse a PRD file.

        Args:
            file_path: Path to the PRD markdown file.

        Returns:
            Parsed PRD document.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If parsing fails.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PRD file not found: {file_path}")

        content = path.read_text(encoding="utf-8")
        return self.parse_string(content, str(path))

    def parse_string(self, content: str, source_path: str | None = None) -> PRDDocument:
        """Parse PRD content from string.

        Args:
            content: PRD markdown content with YAML frontmatter.
            source_path: Optional source path for error reporting.

        Returns:
            Parsed PRD document.

        Raises:
            ValueError: If parsing fails.
        """
        self.warnings = []

        # Parse frontmatter
        post = frontmatter.loads(content)
        metadata = self._parse_metadata(post.metadata)

        # Parse body sections
        body_content = self._parse_body(post.content)

        return PRDDocument(
            metadata=metadata,
            content=body_content,
            source_path=source_path,
        )

    def _parse_metadata(self, meta_dict: dict[str, Any]) -> PRDMetadata:
        """Parse YAML frontmatter metadata.

        Args:
            meta_dict: Raw metadata dictionary from frontmatter.

        Returns:
            Parsed PRD metadata.
        """
        # Handle stack config
        stack_data = meta_dict.get("stack", {})
        if isinstance(stack_data, dict):
            stack = StackConfig(**stack_data)
        else:
            stack = StackConfig()
            self.warnings.append("Invalid stack configuration, using defaults")

        # Handle nextjs config
        nextjs_data = meta_dict.get("nextjs", {})
        if isinstance(nextjs_data, dict):
            nextjs = NextjsConfig(**nextjs_data)
        else:
            nextjs = NextjsConfig()

        # Build metadata
        metadata_dict = {
            "project_name": meta_dict.get("project_name", "unnamed-project"),
            "version": meta_dict.get("version", "1.0.0"),
            "mode": meta_dict.get("mode", "greenfield"),
            "scope": meta_dict.get("scope", "mvp"),
            "stack": stack,
            "nextjs": nextjs,
            "complexity": meta_dict.get("complexity", "auto"),
            "output_dir": meta_dict.get("output_dir", "./output"),
        }

        return PRDMetadata(**metadata_dict)

    def _parse_body(self, body_str: str) -> PRDContent:
        """Parse PRD body content into sections.

        Args:
            body_str: Markdown body content (without frontmatter).

        Returns:
            Parsed PRD content sections.
        """
        sections = self._split_sections(body_str)

        # Extract features from features section
        features: list[Feature] = []
        if "features" in sections:
            features = self._extract_features(sections["features"])

        # Extract pages from pages section
        pages: list[PageRoute] = []
        if "pages" in sections:
            pages = self._extract_pages(sections["pages"])

        return PRDContent(
            overview=sections.get("overview", ""),
            goals=sections.get("goals", ""),
            features=features,
            pages=pages,
            api_requirements=sections.get("api_requirements", ""),
            database_schema=sections.get("database_schema", ""),
            auth_requirements=sections.get("auth_requirements", ""),
            ui_guidelines=sections.get("ui_guidelines", ""),
            performance_requirements=sections.get("performance_requirements", ""),
            security_considerations=sections.get("security_considerations", ""),
            deployment=sections.get("deployment", ""),
            timeline=sections.get("timeline", ""),
            raw_sections=sections,
        )

    def _split_sections(self, body: str) -> dict[str, str]:
        """Split PRD body into sections based on h1 headers.

        Args:
            body: Full markdown body content.

        Returns:
            Dictionary mapping section keys to content.
        """
        sections: dict[str, str] = {}

        # Find only h1 headers (single #) for main sections
        header_pattern = r"^#\s+(.+)$"
        matches = list(re.finditer(header_pattern, body, re.MULTILINE))

        if not matches:
            # No h1 sections found, try h2
            header_pattern = r"^##\s+(.+)$"
            matches = list(re.finditer(header_pattern, body, re.MULTILINE))

        if not matches:
            # No sections found, store entire body as raw
            return {"raw": body.strip()}

        # Extract content between headers
        for i, match in enumerate(matches):
            header_text = match.group(1).strip().lower()
            start_pos = match.end()

            # Find end position (start of next header or end of content)
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(body)

            section_content = body[start_pos:end_pos].strip()

            # Map header to section key
            section_key = self._match_header_to_key(header_text)
            if section_key:
                sections[section_key] = section_content

        return sections

    def _match_header_to_key(self, header_text: str) -> str | None:
        """Match a header text to a section key.

        Args:
            header_text: Lowercase header text.

        Returns:
            Section key if matched, None otherwise.
        """
        # First try exact or prefix matches (numbered sections like "1. overview")
        for key, headers in self.SECTION_HEADERS.items():
            for header in headers:
                # Check for exact match or header starts with pattern
                if header_text == header or header_text.startswith(header + " "):
                    return key
                # Check if header contains the pattern as a word boundary
                if f" {header} " in f" {header_text} " or header_text.endswith(f" {header}"):
                    return key
        return None

    def _extract_features(self, text: str) -> list[Feature]:
        """Extract features from features section.

        Args:
            text: Features section content.

        Returns:
            List of parsed features.
        """
        features: list[Feature] = []

        # Split by feature headers (## Feature only, not ###)
        # Pattern matches: ## Feature Name: Title or ## Feature: Title
        feature_pattern = r"(?:^|\n)##\s+(?:Feature\s+)?\d*\s*:?\s*([^\n]+)"
        matches = list(re.finditer(feature_pattern, text, re.IGNORECASE))

        if not matches:
            # Try alternative pattern for bullet features
            return features

        for i, match in enumerate(matches):
            feature_name = match.group(1).strip()
            start_pos = match.end()

            # Find end of this feature section
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)

            feature_text = text[start_pos:end_pos]

            # Extract priority (from both header and body)
            priority = self._extract_priority(feature_name + "\n" + feature_text)

            # Extract user story
            user_story = self._extract_field(feature_text, "user story")

            # Extract description (first paragraph after header)
            description = ""
            desc_match = re.search(
                r"(?:###?\s+[^\n]+\n+)([^#].*?)(?=\n+###|\n+##|\Z)",
                feature_text,
                re.DOTALL,
            )
            if desc_match:
                description = desc_match.group(1).strip()

            # Extract components checklist
            components = self._extract_checklist(feature_text, "components")

            # Extract acceptance criteria
            criteria = self._extract_checklist(feature_text, "acceptance criteria")

            feature = Feature(
                name=feature_name,
                priority=priority,
                description=description,
                user_story=user_story,
                components=components,
                criteria=criteria,
            )
            features.append(feature)

        return features

    def _extract_priority(self, text: str) -> FeaturePriority:
        """Extract priority level from feature text.

        Args:
            text: Feature section text.

        Returns:
            Feature priority level.
        """
        # Look for priority markers
        priority_patterns = [
            (r"\*\*priority:\s*\*\*\s*(p0)\b", FeaturePriority.P0),
            (r"\*\*priority:\s*\*\*\s*(p1)\b", FeaturePriority.P1),
            (r"\*\*priority:\s*\*\*\s*(p2)\b", FeaturePriority.P2),
            (r"\*\*priority:\s*(p0)\b", FeaturePriority.P0),
            (r"\*\*priority:\s*(p1)\b", FeaturePriority.P1),
            (r"\*\*priority:\s*(p2)\b", FeaturePriority.P2),
            (r"priority:\s*(p0)\b", FeaturePriority.P0),
            (r"priority:\s*(p1)\b", FeaturePriority.P1),
            (r"priority:\s*(p2)\b", FeaturePriority.P2),
            (r"\(p0\)", FeaturePriority.P0),
            (r"\(p1\)", FeaturePriority.P1),
            (r"\(p2\)", FeaturePriority.P2),
            (r"must have", FeaturePriority.P0),
            (r"should have", FeaturePriority.P1),
            (r"nice to have", FeaturePriority.P2),
        ]

        text_lower = text.lower()
        for pattern, priority in priority_patterns:
            if re.search(pattern, text_lower):
                return priority

        return FeaturePriority.P1  # Default to P1

    def _extract_field(self, text: str, field_name: str) -> str:
        """Extract a field value from text.

        Args:
            text: Text to search in.
            field_name: Name of the field to extract.

        Returns:
            Extracted field value or empty string.
        """
        # Match field header followed by content until next header or list
        pattern = rf"(?:###?\s+)?{re.escape(field_name)}[:\s]*\n+([^#\n].*?)(?=\n+###|\n+##|\n+-|\n+\*|\Z)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try alternative: match after field name in bold
        pattern = rf"\*\*{re.escape(field_name)}:?\*\*\s*\n+([^#].*?)(?=\n+###|\n+##|\Z)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

        return ""

    def _extract_checklist(self, text: str, section_name: str) -> list[str]:
        """Extract checklist items from a section.

        Args:
            text: Text to search in.
            section_name: Name of the checklist section.

        Returns:
            List of checklist item strings.
        """
        items: list[str] = []

        # Find the section
        pattern = rf"(?:###?\s+)?{re.escape(section_name)}[:\s]*\n+(.*?)(?=\n+###|\n+##|\Z)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if match:
            section_text = match.group(1)
            # Extract checklist items (- [ ] or - [x])
            checklist_pattern = r"-\s*\[\s*[xX]?\s*\]\s*(.+)$"
            items = re.findall(checklist_pattern, section_text, re.MULTILINE)

        return items

    def _extract_pages(self, text: str) -> list[PageRoute]:
        """Extract page routes from pages section.

        Args:
            text: Pages section content.

        Returns:
            List of page routes.
        """
        pages: list[PageRoute] = []

        # Look for markdown tables
        table_pattern = r"\|([^\n]+)\|\n\|[-:\s|]+\|\n((?:\|[^\n]+\|\n?)+)"
        table_match = re.search(table_pattern, text)

        if table_match:
            header_line = table_match.group(1)
            data_lines = table_match.group(2).strip().split("\n")

            # Parse headers
            headers = [h.strip().lower() for h in header_line.split("|") if h.strip()]

            # Find column indices
            route_idx = self._find_column_index(headers, ["route", "path", "url"])
            name_idx = self._find_column_index(headers, ["page name", "name", "page"])
            desc_idx = self._find_column_index(headers, ["description", "desc"])
            auth_idx = self._find_column_index(headers, ["auth required", "auth", "protected"])

            for line in data_lines:
                if not line.strip() or not line.startswith("|"):
                    continue

                cells = [c.strip() for c in line.split("|") if c.strip() or c == ""]
                # Handle empty cells properly
                cells = [c.strip() for c in line[1:-1].split("|")]

                if route_idx is not None and route_idx < len(cells):
                    route = cells[route_idx].strip()
                    if route and route.lower() not in ["route", "path"]:
                        name = cells[name_idx].strip() if name_idx is not None and name_idx < len(cells) else ""
                        description = cells[desc_idx].strip() if desc_idx is not None and desc_idx < len(cells) else ""
                        auth_text = cells[auth_idx].strip() if auth_idx is not None and auth_idx < len(cells) else ""
                        auth_required = auth_text.lower() in ["yes", "true", "required", "y"]

                        pages.append(PageRoute(
                            route=route,
                            name=name or route,
                            description=description,
                            auth_required=auth_required,
                        ))

        return pages

    def _find_column_index(self, headers: list[str], possible_names: list[str]) -> int | None:
        """Find column index by possible header names.

        Args:
            headers: List of header names.
            possible_names: Possible names for the column.

        Returns:
            Column index or None if not found.
        """
        for name in possible_names:
            for i, header in enumerate(headers):
                if name in header:
                    return i
        return None


def validate_prd(doc: PRDDocument) -> list[str]:
    """Validate a PRD document and return warnings.

    Args:
        doc: Parsed PRD document.

    Returns:
        List of validation warnings.
    """
    warnings: list[str] = []

    # Check metadata
    if not doc.metadata.project_name or doc.metadata.project_name == "unnamed-project":
        warnings.append("Project name is not set or uses default value")

    # Check features
    if not doc.content.features:
        warnings.append("No features defined in PRD")
    else:
        p0_count = len(doc.get_mvp_features())
        if p0_count == 0:
            warnings.append("No P0 (must-have) features defined")

    # Check pages
    if not doc.content.pages:
        warnings.append("No page routes defined")

    # Check for empty sections
    empty_sections = []
    if not doc.content.overview:
        empty_sections.append("overview")
    if not doc.content.goals:
        empty_sections.append("goals")

    if empty_sections:
        warnings.append(f"Empty sections: {', '.join(empty_sections)}")

    return warnings


def parse_prd(file_path: str | Path) -> PRDDocument:
    """Convenience function to parse a PRD file.

    Args:
        file_path: Path to the PRD markdown file.

    Returns:
        Parsed PRD document.
    """
    parser = PRDParser()
    return parser.parse_file(file_path)
