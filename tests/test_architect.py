"""Tests for Task Architect Agent."""

import pytest
from pathlib import Path

from orkit_crew.agents.architect import TaskArchitectAgent
from orkit_crew.core.prd_parser import PRDDocument, PRDMetadata, PRDContent, Feature, FeaturePriority
from orkit_crew.core.session import SessionManager


class TestTaskArchitectAgent:
    """Test Task Architect Agent functionality."""

    @pytest.fixture
    def sample_prd(self) -> PRDDocument:
        """Create a sample PRD document."""
        return PRDDocument(
            metadata=PRDMetadata(
                project_name="test-app",
                version="1.0.0",
            ),
            content=PRDContent(
                overview="A test application.",
                goals="Test goals.",
                features=[
                    Feature(name="Feature 1", priority=FeaturePriority.P0),
                    Feature(name="Feature 2", priority=FeaturePriority.P1),
                ],
            ),
        )

    @pytest.fixture
    def sample_analysis(self) -> str:
        """Sample analysis content."""
        return """
# Analysis

## Summary
Test project for task management.

## Key Features
- Feature 1: P0 priority
- Feature 2: P1 priority

## Complexity Assessment
Medium complexity.
"""

    def test_agent_properties(self) -> None:
        """Test agent role, goal, and backstory."""
        agent = TaskArchitectAgent()

        assert agent.role == "Task Architect"
        assert "task plan" in agent.goal.lower()
        assert "Next.js" in agent.backstory

    def test_parse_tasks(self) -> None:
        """Test task parsing from plan content."""
        agent = TaskArchitectAgent()

        plan_content = """
### 3. Tasks

**Task 1: Setup Project**
- **Type:** setup
- **Files:** `package.json`, `next.config.js`
- **Description:** Initialize project
- **Dependencies:** None
- **Complexity:** low
- **Acceptance Criteria:** Project runs

**Task 2: Create Home Page**
- **Type:** page
- **Files:** `src/app/page.tsx`
- **Description:** Create home page
- **Dependencies:** Task 1
- **Complexity:** medium
- **Acceptance Criteria:** Page loads
"""

        tasks = agent.parse_tasks(plan_content)

        assert len(tasks) == 2
        assert tasks[0]["number"] == 1
        assert tasks[0]["title"] == "Setup Project"
        assert tasks[0]["type"] == "setup"
        assert tasks[0]["files"] == ["package.json", "next.config.js"]
        assert tasks[0]["complexity"] == "low"

        assert tasks[1]["number"] == 2
        assert tasks[1]["dependencies"] == [1]

    def test_parse_tasks_with_various_formats(self) -> None:
        """Test parsing tasks with different formatting."""
        agent = TaskArchitectAgent()

        plan_content = """
**Task 1: Config**
- Type: config
- Files: `tsconfig.json`
- Description: Setup TypeScript
- Dependencies: None
- Complexity: low
- Acceptance Criteria: Compiles
"""

        tasks = agent.parse_tasks(plan_content)

        assert len(tasks) == 1
        assert tasks[0]["type"] == "config"

    def test_get_task_by_number(self) -> None:
        """Test getting task by number."""
        agent = TaskArchitectAgent()

        agent.tasks = [
            {"number": 1, "title": "Task 1"},
            {"number": 2, "title": "Task 2"},
        ]

        task = agent.get_task_by_number(1)
        assert task is not None
        assert task["title"] == "Task 1"

        missing = agent.get_task_by_number(99)
        assert missing is None

    def test_get_tasks_by_type(self) -> None:
        """Test getting tasks by type."""
        agent = TaskArchitectAgent()

        agent.tasks = [
            {"number": 1, "type": "setup"},
            {"number": 2, "type": "component"},
            {"number": 3, "type": "setup"},
        ]

        setup_tasks = agent.get_tasks_by_type("setup")
        assert len(setup_tasks) == 2

    def test_get_tasks_by_complexity(self) -> None:
        """Test getting tasks by complexity."""
        agent = TaskArchitectAgent()

        agent.tasks = [
            {"number": 1, "complexity": "low"},
            {"number": 2, "complexity": "high"},
            {"number": 3, "complexity": "low"},
        ]

        low_tasks = agent.get_tasks_by_complexity("low")
        assert len(low_tasks) == 2

    def test_build_plan_prompt(self, sample_prd: PRDDocument, sample_analysis: str) -> None:
        """Test plan prompt building."""
        agent = TaskArchitectAgent()

        prompt = agent._build_plan_prompt(sample_prd, sample_analysis, mvp_only=True)

        assert "test-app" in prompt
        assert "MVP features only" in prompt
        assert "Tech Stack" in prompt
        assert "Project Structure" in prompt
        assert "Tasks" in prompt
        assert "Feature 1" in prompt
        assert "Analysis" in prompt

    def test_build_plan_prompt_full_scope(self, sample_prd: PRDDocument, sample_analysis: str) -> None:
        """Test prompt with full scope."""
        agent = TaskArchitectAgent()

        prompt = agent._build_plan_prompt(sample_prd, sample_analysis, mvp_only=False)

        assert "All features (full scope)" in prompt
        assert "Feature 2" in prompt  # P1 feature included

    def test_agent_with_session_manager(self, tmp_path: Path) -> None:
        """Test agent integration with session manager."""
        session_manager = SessionManager(tmp_path)
        session_manager.init_session(prd_file="test.prd.md")

        agent = TaskArchitectAgent(session_manager=session_manager)

        assert agent.session_manager is session_manager

    def test_parse_empty_tasks(self) -> None:
        """Test parsing tasks from empty content."""
        agent = TaskArchitectAgent()

        tasks = agent.parse_tasks("")
        assert tasks == []

        tasks = agent.parse_tasks("No tasks here")
        assert tasks == []
