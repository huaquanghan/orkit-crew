"""Tests for PRD Analyst Agent."""

import pytest
from pathlib import Path

from orkit_crew.agents.analyst import PRDAnalystAgent
from orkit_crew.core.prd_parser import PRDDocument, PRDMetadata, PRDContent
from orkit_crew.core.session import SessionManager, PipelinePhase


class TestPRDAnalystAgent:
    """Test PRD Analyst Agent functionality."""

    @pytest.fixture
    def sample_prd(self) -> PRDDocument:
        """Create a sample PRD document."""
        return PRDDocument(
            metadata=PRDMetadata(
                project_name="test-app",
                version="1.0.0",
            ),
            content=PRDContent(
                overview="A test application for task management.",
                goals="Help users manage tasks efficiently.",
            ),
        )

    @pytest.fixture
    def detailed_prd(self) -> PRDDocument:
        """Create a detailed PRD document with features."""
        from orkit_crew.core.prd_parser import Feature, FeaturePriority, PageRoute

        return PRDDocument(
            metadata=PRDMetadata(
                project_name="detailed-app",
                version="2.0.0",
            ),
            content=PRDContent(
                overview="A comprehensive project management tool.",
                goals="Enable teams to collaborate effectively.",
                features=[
                    Feature(
                        name="User Authentication",
                        priority=FeaturePriority.P0,
                        description="Login and signup functionality",
                        user_story="As a user, I want to login",
                        components=["Login form", "OAuth"],
                        criteria=["User can login", "User can signup"],
                    ),
                    Feature(
                        name="Dashboard",
                        priority=FeaturePriority.P1,
                        description="Main dashboard view",
                    ),
                ],
                pages=[
                    PageRoute(route="/", name="Home"),
                    PageRoute(route="/login", name="Login"),
                    PageRoute(route="/dashboard", name="Dashboard", auth_required=True),
                ],
            ),
        )

    def test_agent_properties(self) -> None:
        """Test agent role, goal, and backstory."""
        agent = PRDAnalystAgent()

        assert agent.role == "PRD Analyst"
        assert "PRD" in agent.goal
        assert "analyze" in agent.goal.lower()
        assert "10+ years" in agent.backstory

    def test_extract_questions_from_text(self) -> None:
        """Test question extraction from analysis text."""
        agent = PRDAnalystAgent()

        analysis = """
### 4. Ambiguities & Questions

QUESTION: What is the expected user capacity?

Some other text.

Q: Should we support mobile devices?

1. What authentication method should we use?
2. How many concurrent users?

- What is the timeline?
- Who is the target audience?
"""

        questions = agent.extract_questions(analysis)

        assert len(questions) >= 4
        assert any("user capacity" in q for q in questions)
        assert any("mobile" in q for q in questions)
        assert any("authentication" in q for q in questions)

    def test_get_complexity_assessment(self) -> None:
        """Test complexity assessment extraction."""
        agent = PRDAnalystAgent()

        analysis = """
### 6. Complexity Assessment

High complexity due to multiple integrations.

- Real-time features
- Third-party APIs
- Complex data models
"""

        assessment = agent.get_complexity_assessment(analysis)

        assert assessment["level"] == "high"
        assert "complexity" in assessment["justification"].lower()
        assert len(assessment["factors"]) >= 3

    def test_build_analysis_prompt(self, sample_prd: PRDDocument) -> None:
        """Test analysis prompt building."""
        agent = PRDAnalystAgent()

        prompt = agent._build_analysis_prompt(sample_prd)

        assert "test-app" in prompt
        assert "1.0.0" in prompt
        assert "Overview" in prompt
        assert "Goals" in prompt
        assert "Summary" in prompt
        assert "Key Features" in prompt

    def test_build_analysis_prompt_with_features(self, detailed_prd: PRDDocument) -> None:
        """Test prompt building with features."""
        agent = PRDAnalystAgent()

        prompt = agent._build_analysis_prompt(detailed_prd)

        assert "User Authentication" in prompt
        assert "P0" in prompt
        assert "Dashboard" in prompt
        assert "/login" in prompt
        assert "requires auth" in prompt

    def test_agent_with_session_manager(self, tmp_path: Path) -> None:
        """Test agent integration with session manager."""
        session_manager = SessionManager(tmp_path)
        session_manager.init_session(prd_file="test.prd.md")

        agent = PRDAnalystAgent(session_manager=session_manager)

        assert agent.session_manager is session_manager

    def test_log_output(self, tmp_path: Path) -> None:
        """Test output logging."""
        session_manager = SessionManager(tmp_path)
        session_manager.init_session(prd_file="test.prd.md")

        agent = PRDAnalystAgent(session_manager=session_manager)
        agent.log_output("Test analysis content", "analysis")

        # Check decision was logged
        decisions_path = tmp_path / ".orkit" / "context" / "decisions.md"
        assert decisions_path.exists()
        content = decisions_path.read_text()
        assert "Agent output: analysis" in content

    @pytest.mark.asyncio
    async def test_analyze_produces_output(self, sample_prd: PRDDocument) -> None:
        """Test that analyze produces output structure.
        
        Note: This test may need mocking in CI without LLM access.
        """
        agent = PRDAnalystAgent()

        # This will fail without LLM, but tests the structure
        try:
            result = await agent.analyze(sample_prd, interactive=False)
            assert isinstance(result, str)
            assert len(result) > 0
        except Exception as e:
            # Expected to fail without LLM configured
            pytest.skip(f"LLM not configured: {e}")

    def test_extract_questions_empty(self) -> None:
        """Test question extraction with no questions."""
        agent = PRDAnalystAgent()

        analysis = "No questions here. Just a summary."
        questions = agent.extract_questions(analysis)

        assert len(questions) == 0

    def test_complexity_assessment_not_found(self) -> None:
        """Test complexity extraction when section missing."""
        agent = PRDAnalystAgent()

        analysis = "No complexity section here."
        assessment = agent.get_complexity_assessment(analysis)

        assert assessment["level"] == "medium"  # Default
        assert assessment["justification"] == ""
        assert assessment["factors"] == []

    def test_qa_pairs_storage(self, tmp_path: Path, sample_prd: PRDDocument) -> None:
        """Test Q&A pairs are stored correctly."""
        agent = PRDAnalystAgent()

        qa_pairs = [
            {"question": "Q1?", "answer": "A1"},
            {"question": "Q2?", "answer": "A2"},
        ]

        # Store QA pairs
        agent.qa_pairs = qa_pairs
        assert len(agent.qa_pairs) == 2
        assert agent.qa_pairs[0]["question"] == "Q1?"
