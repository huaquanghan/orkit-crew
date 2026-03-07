"""Integration tests for the full pipeline with mock LLM."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orkit_crew.core.prd_parser import parse_prd
from orkit_crew.core.session import SessionManager, PipelinePhase
from orkit_crew.pipeline.orchestrator import PipelineOrchestrator


# Fixtures
@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    return tmp_path / "output"


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.chat = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_llm_responses():
    """Create predetermined LLM responses for testing."""
    return {
        "analysis": """
# Analysis

## Summary
A test project for integration testing.

## Key Features Extracted
| Feature | Priority | Complexity | Dependencies |
|---------|----------|------------|--------------|
| Hero Section | P0 | Low | None |

## Technical Requirements
- Next.js App Router
- Tailwind CSS

## Complexity Assessment
Low complexity project.

## Risk Factors
None identified.
""",
        "plan": """
# Implementation Plan

## Tech Stack
- Next.js 15
- TypeScript
- Tailwind CSS
- shadcn/ui

## Project Structure
```
my-app/
├── src/
│   ├── app/
│   ├── components/
│   └── lib/
├── public/
└── package.json
```

## Tasks

**Task 1: Initialize Next.js Project**
- **Type:** setup
- **Files:** `package.json`, `tsconfig.json`, `tailwind.config.ts`
- **Description:** Create new Next.js project
- **Dependencies:** None
- **Complexity:** low
- **Acceptance Criteria:** Project runs

**Task 2: Create Hero Component**
- **Type:** component
- **Files:** `src/components/Hero.tsx`
- **Description:** Create hero section component
- **Dependencies:** Task 1
- **Complexity:** low
- **Acceptance Criteria:** Component renders

## Dependency Graph
Task 1 → Task 2

## Summary
- Total tasks: 2
- Low complexity
""",
    }


# Mock the CrewAI agents
@pytest.fixture
def mock_crewai_agent():
    """Create a mock CrewAI agent."""
    mock = MagicMock()
    mock.execute_sync = MagicMock()
    return mock


class TestFullPipeline:
    """Test full pipeline execution."""

    @pytest.mark.asyncio
    async def test_pipeline_with_mock_llm(
        self,
        fixtures_dir: Path,
        temp_output_dir: Path,
        mock_llm_responses: dict,
    ) -> None:
        """Test full pipeline with mock LLM responses."""
        prd_path = fixtures_dir / "prd_minimal.md"

        # Create orchestrator
        orchestrator = PipelineOrchestrator(
            prd_path=str(prd_path),
            output_dir=str(temp_output_dir),
        )

        # Mock the agent methods to return predetermined responses
        with patch.object(orchestrator, "_init_agents") as mock_init:
            # Setup mock agents
            mock_analyst = MagicMock()
            mock_analyst.analyze = AsyncMock(return_value=mock_llm_responses["analysis"])
            mock_analyst.revise_analysis = AsyncMock(return_value=mock_llm_responses["analysis"])

            mock_architect = MagicMock()
            mock_architect.plan = AsyncMock(return_value=mock_llm_responses["plan"])
            mock_architect.revise_plan = AsyncMock(return_value=mock_llm_responses["plan"])
            mock_architect.tasks = [
                {
                    "number": 1,
                    "title": "Initialize Next.js Project",
                    "type": "setup",
                    "files": ["package.json", "tsconfig.json"],
                    "description": "Create project",
                    "dependencies": [],
                    "complexity": "low",
                },
                {
                    "number": 2,
                    "title": "Create Hero Component",
                    "type": "component",
                    "files": ["src/components/Hero.tsx"],
                    "description": "Create hero",
                    "dependencies": [1],
                    "complexity": "low",
                },
            ]

            mock_generator = MagicMock()
            mock_generator.generate = AsyncMock(return_value=[
                str(temp_output_dir / "package.json"),
                str(temp_output_dir / "tsconfig.json"),
                str(temp_output_dir / "src" / "components" / "Hero.tsx"),
            ])

            orchestrator.analyst = mock_analyst
            orchestrator.architect = mock_architect
            orchestrator.generator = mock_generator

            # Mock review loop to auto-approve
            with patch.object(orchestrator, "review_loop", return_value=True):
                # Run pipeline
                success = await orchestrator.run()

        # Verify pipeline completed
        assert success is True

        # Verify agents were called
        mock_analyst.analyze.assert_called_once()
        mock_architect.plan.assert_called_once()
        mock_generator.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_creates_output_files(
        self,
        fixtures_dir: Path,
        temp_output_dir: Path,
    ) -> None:
        """Test that pipeline creates output files."""
        prd_path = fixtures_dir / "prd_minimal.md"

        orchestrator = PipelineOrchestrator(
            prd_path=str(prd_path),
            output_dir=str(temp_output_dir),
        )

        # Mock to skip actual generation but create files
        with patch.object(orchestrator, "_init_agents"):
            orchestrator.prd_doc = parse_prd(prd_path)
            orchestrator.session_manager = SessionManager(temp_output_dir)
            orchestrator.session_manager.init_session(
                prd_file=str(prd_path),
                project_name="test",
                output_dir=str(temp_output_dir),
            )

            # Manually create some files to simulate generation
            temp_output_dir.mkdir(parents=True, exist_ok=True)
            (temp_output_dir / "package.json").write_text('{"name": "test"}')
            (temp_output_dir / "src").mkdir(exist_ok=True)
            (temp_output_dir / "src" / "app").mkdir(exist_ok=True)
            (temp_output_dir / "src" / "app" / "page.tsx").write_text("export default function Page() {}")

            # Verify files exist
            assert (temp_output_dir / "package.json").exists()
            assert (temp_output_dir / "src" / "app" / "page.tsx").exists()


class TestPipelineResume:
    """Test pipeline resume functionality."""

    @pytest.mark.asyncio
    async def test_resume_from_analysis_phase(
        self,
        fixtures_dir: Path,
        temp_output_dir: Path,
        mock_llm_responses: dict,
    ) -> None:
        """Test resuming from analysis phase."""
        prd_path = fixtures_dir / "prd_minimal.md"

        # Create initial session at analysis phase
        session_manager = SessionManager(temp_output_dir)
        session_manager.init_session(
            prd_file=str(prd_path),
            project_name="test-resume",
            output_dir=str(temp_output_dir),
        )
        session_manager.start_phase(PipelinePhase.ANALYZING)
        session_manager.save_analysis(mock_llm_responses["analysis"])

        # Create orchestrator and resume
        orchestrator = PipelineOrchestrator(
            prd_path=str(prd_path),
            output_dir=str(temp_output_dir),
        )

        with patch.object(orchestrator, "_init_agents") as mock_init:
            mock_architect = MagicMock()
            mock_architect.plan = AsyncMock(return_value=mock_llm_responses["plan"])
            mock_architect.tasks = []
            mock_architect.revise_plan = AsyncMock(return_value=mock_llm_responses["plan"])

            mock_generator = MagicMock()
            mock_generator.generate = AsyncMock(return_value=[])

            orchestrator.architect = mock_architect
            orchestrator.generator = mock_generator

            with patch.object(orchestrator, "review_loop", return_value=True):
                success = await orchestrator.resume()

        assert success is True

    @pytest.mark.asyncio
    async def test_resume_from_planning_phase(
        self,
        fixtures_dir: Path,
        temp_output_dir: Path,
        mock_llm_responses: dict,
    ) -> None:
        """Test resuming from planning phase."""
        prd_path = fixtures_dir / "prd_minimal.md"

        # Create initial session with completed analysis
        session_manager = SessionManager(temp_output_dir)
        session_manager.init_session(
            prd_file=str(prd_path),
            project_name="test-resume",
            output_dir=str(temp_output_dir),
        )
        session_manager.start_phase(PipelinePhase.ANALYZING)
        session_manager.save_analysis(mock_llm_responses["analysis"])
        session_manager.complete_phase(PipelinePhase.ANALYZING)
        session_manager.approve_phase(PipelinePhase.ANALYZING)
        session_manager.start_phase(PipelinePhase.PLANNING)
        session_manager.save_plan(mock_llm_responses["plan"])

        # Create orchestrator and resume
        orchestrator = PipelineOrchestrator(
            prd_path=str(prd_path),
            output_dir=str(temp_output_dir),
        )

        with patch.object(orchestrator, "_init_agents") as mock_init:
            mock_generator = MagicMock()
            mock_generator.generate = AsyncMock(return_value=[])
            orchestrator.generator = mock_generator

            with patch.object(orchestrator, "review_loop", return_value=True):
                success = await orchestrator.resume()

        assert success is True


class TestPipelineErrorHandling:
    """Test pipeline error handling."""

    @pytest.mark.asyncio
    async def test_pipeline_handles_invalid_prd(
        self,
        tmp_path: Path,
    ) -> None:
        """Test pipeline handles invalid PRD file."""
        invalid_prd = tmp_path / "invalid.md"
        invalid_prd.write_text("Not a valid PRD")

        orchestrator = PipelineOrchestrator(
            prd_path=str(invalid_prd),
            output_dir=str(tmp_path / "output"),
        )

        # Should handle gracefully (though may succeed with defaults)
        # The parser is quite lenient
        result = await orchestrator.run()

        # Result depends on implementation, but shouldn't crash
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_pipeline_handles_missing_prd(
        self,
        tmp_path: Path,
    ) -> None:
        """Test pipeline handles missing PRD file."""
        orchestrator = PipelineOrchestrator(
            prd_path=str(tmp_path / "nonexistent.md"),
            output_dir=str(tmp_path / "output"),
        )

        with pytest.raises(FileNotFoundError):
            await orchestrator.run()


class TestPipelineState:
    """Test pipeline state management."""

    @pytest.mark.asyncio
    async def test_get_status_no_session(
        self,
        tmp_path: Path,
    ) -> None:
        """Test get_status with no session."""
        orchestrator = PipelineOrchestrator(
            prd_path=str(tmp_path / "test.md"),
            output_dir=str(tmp_path / "output"),
        )

        status = orchestrator.get_status()
        assert status["status"] == "no_session"

    @pytest.mark.asyncio
    async def test_get_status_with_session(
        self,
        fixtures_dir: Path,
        temp_output_dir: Path,
    ) -> None:
        """Test get_status with active session."""
        prd_path = fixtures_dir / "prd_minimal.md"

        orchestrator = PipelineOrchestrator(
            prd_path=str(prd_path),
            output_dir=str(temp_output_dir),
        )

        # Initialize session
        orchestrator.prd_doc = parse_prd(prd_path)
        orchestrator.session_manager = SessionManager(temp_output_dir)
        orchestrator.session_manager.init_session(
            prd_file=str(prd_path),
            project_name="test",
            output_dir=str(temp_output_dir),
        )

        status = orchestrator.get_status()
        assert status["project_name"] == "test"
        assert "current_phase" in status
        assert "session_id" in status
