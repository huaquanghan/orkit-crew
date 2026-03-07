"""Tests for session management."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orkit_crew.core.session import (
    SessionManager,
    SessionData,
    PipelinePhase,
    PhaseStatus,
    PhaseState,
)


# Fixtures
@pytest.fixture
def temp_session_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for session testing."""
    return tmp_path / "test_project"


@pytest.fixture
def session_manager(temp_session_dir: Path) -> SessionManager:
    """Create a session manager with temporary directory."""
    return SessionManager(temp_session_dir)


@pytest.fixture
def initialized_session(session_manager: SessionManager) -> SessionData:
    """Create and return an initialized session."""
    return session_manager.init_session(
        prd_file="/path/to/prd.md",
        project_name="test-project",
        output_dir="./output",
    )


# Test session initialization
class TestSessionInitialization:
    """Test session initialization."""

    def test_init_session_creates_directory_structure(
        self,
        session_manager: SessionManager,
        temp_session_dir: Path,
    ) -> None:
        """Test that init_session creates .orkit directory structure."""
        session_manager.init_session(
            prd_file="prd.md",
            project_name="test",
        )

        assert (temp_session_dir / ".orkit").exists()
        assert (temp_session_dir / ".orkit" / "reviews").exists()
        assert (temp_session_dir / ".orkit" / "context").exists()

    def test_init_session_creates_session_json(
        self,
        session_manager: SessionManager,
        temp_session_dir: Path,
    ) -> None:
        """Test that init_session creates session.json."""
        session_manager.init_session(
            prd_file="prd.md",
            project_name="test",
        )

        session_file = temp_session_dir / ".orkit" / "session.json"
        assert session_file.exists()

        # Verify content
        data = json.loads(session_file.read_text())
        assert data["project_name"] == "test"
        assert data["prd_file"] == "prd.md"
        assert "session_id" in data

    def test_session_data_structure(self, initialized_session: SessionData) -> None:
        """Test session data structure."""
        assert initialized_session.project_name == "test-project"
        assert initialized_session.prd_file == "/path/to/prd.md"
        assert initialized_session.output_dir == "./output"
        assert len(initialized_session.session_id) == 8

    def test_session_has_phase_states(self, initialized_session: SessionData) -> None:
        """Test that session has phase states."""
        assert isinstance(initialized_session.analysis, PhaseState)
        assert isinstance(initialized_session.planning, PhaseState)
        assert isinstance(initialized_session.generation, PhaseState)

        # All should start as pending
        assert initialized_session.analysis.status == PhaseStatus.PENDING
        assert initialized_session.planning.status == PhaseStatus.PENDING
        assert initialized_session.generation.status == PhaseStatus.PENDING


# Test session loading
class TestSessionLoading:
    """Test session loading and persistence."""

    def test_load_session(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test loading an existing session."""
        # Create new manager pointing to same directory
        new_manager = SessionManager(session_manager.base_dir)
        loaded = new_manager.load_session()

        assert loaded.session_id == initialized_session.session_id
        assert loaded.project_name == initialized_session.project_name

    def test_has_session_true(self, session_manager: SessionManager) -> None:
        """Test has_session returns True when session exists."""
        session_manager.init_session(prd_file="prd.md", project_name="test")
        assert session_manager.has_session() is True

    def test_has_session_false(self, temp_session_dir: Path) -> None:
        """Test has_session returns False when no session exists."""
        manager = SessionManager(temp_session_dir)
        assert manager.has_session() is False

    def test_load_session_not_found(self, temp_session_dir: Path) -> None:
        """Test loading non-existent session raises error."""
        manager = SessionManager(temp_session_dir)
        with pytest.raises(FileNotFoundError):
            manager.load_session()


# Test phase transitions
class TestPhaseTransitions:
    """Test phase state transitions."""

    def test_start_phase(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test starting a phase."""
        session_manager.start_phase(PipelinePhase.ANALYZING)

        assert session_manager.session.current_phase == PipelinePhase.ANALYZING
        assert session_manager.session.analysis.status == PhaseStatus.IN_PROGRESS
        assert session_manager.session.analysis.started_at is not None

    def test_complete_phase(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test completing a phase."""
        session_manager.start_phase(PipelinePhase.ANALYZING)
        session_manager.complete_phase(PipelinePhase.ANALYZING)

        assert session_manager.session.analysis.status == PhaseStatus.AWAITING_REVIEW
        assert session_manager.session.analysis.completed_at is not None
        assert session_manager.session.current_phase == PipelinePhase.ANALYSIS_REVIEW

    def test_approve_phase(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test approving a phase."""
        session_manager.start_phase(PipelinePhase.ANALYZING)
        session_manager.complete_phase(PipelinePhase.ANALYZING)
        session_manager.approve_phase(PipelinePhase.ANALYZING)

        assert session_manager.session.analysis.status == PhaseStatus.APPROVED
        assert session_manager.session.current_phase == PipelinePhase.PLANNING

    def test_request_revision(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test requesting a revision."""
        session_manager.start_phase(PipelinePhase.ANALYZING)
        session_manager.complete_phase(PipelinePhase.ANALYZING)
        session_manager.request_revision(PipelinePhase.ANALYZING, "Needs more detail")

        assert session_manager.session.analysis.status == PhaseStatus.REVISION_REQUESTED
        assert session_manager.session.analysis.version == 2
        assert session_manager.session.total_revisions == 1
        assert session_manager.session.current_phase == PipelinePhase.ANALYZING

    def test_fail_phase(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test failing a phase."""
        session_manager.start_phase(PipelinePhase.ANALYZING)
        session_manager.fail_phase(PipelinePhase.ANALYZING, "LLM API error")

        assert session_manager.session.analysis.status == PhaseStatus.FAILED
        assert session_manager.session.analysis.error == "LLM API error"
        assert session_manager.session.current_phase == PipelinePhase.FAILED

    def test_phase_version_increment(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test phase version increments on revision."""
        session_manager.start_phase(PipelinePhase.ANALYZING)
        session_manager.complete_phase(PipelinePhase.ANALYZING)

        assert session_manager.session.analysis.version == 1

        session_manager.request_revision(PipelinePhase.ANALYZING, "Fix 1")
        assert session_manager.session.analysis.version == 2

        session_manager.complete_phase(PipelinePhase.ANALYZING)
        session_manager.request_revision(PipelinePhase.ANALYZING, "Fix 2")
        assert session_manager.session.analysis.version == 3


# Test content saving
class TestContentSaving:
    """Test saving analysis and plan content."""

    def test_save_analysis(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test saving analysis content."""
        content = "# Analysis\n\nThis is the analysis."
        path = session_manager.save_analysis(content)

        assert path.exists()
        assert path.read_text() == content

    def test_get_analysis(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test retrieving analysis content."""
        content = "# Analysis\n\nTest content."
        session_manager.save_analysis(content)

        retrieved = session_manager.get_analysis()
        assert retrieved == content

    def test_save_plan(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test saving plan content."""
        content = "# Plan\n\nThis is the plan."
        path = session_manager.save_plan(content)

        assert path.exists()
        assert path.read_text() == content

    def test_get_plan(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test retrieving plan content."""
        content = "# Plan\n\nTest content."
        session_manager.save_plan(content)

        retrieved = session_manager.get_plan()
        assert retrieved == content

    def test_save_creates_backup(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test that saving creates backup of previous version."""
        # First save
        session_manager.save_analysis("Version 1")

        # Increment version and save again
        session_manager.session.analysis.version = 2
        session_manager.save_analysis("Version 2")

        # Check backup exists
        backup_path = session_manager.reviews_dir / "analysis_v1.md"
        assert backup_path.exists()
        assert backup_path.read_text() == "Version 1"


# Test file tracking
class TestFileTracking:
    """Test generated file tracking."""

    def test_add_generated_file(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test adding generated files."""
        session_manager.add_generated_file("/path/to/file1.tsx")
        session_manager.add_generated_file("/path/to/file2.tsx")

        assert "/path/to/file1.tsx" in session_manager.session.generated_files
        assert "/path/to/file2.tsx" in session_manager.session.generated_files

    def test_track_file(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test tracking file with task context."""
        session_manager.track_file("/path/to/component.tsx", task_title="Create Button")

        assert "/path/to/component.tsx" in session_manager.session.generated_files

    def test_no_duplicate_files(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test that duplicate files are not added."""
        session_manager.add_generated_file("/path/to/file.tsx")
        session_manager.add_generated_file("/path/to/file.tsx")

        assert session_manager.session.generated_files.count("/path/to/file.tsx") == 1


# Test logging
class TestLogging:
    """Test conversation and decision logging."""

    def test_log_conversation(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test logging conversation entries."""
        session_manager.log_conversation("user", "Hello")
        session_manager.log_conversation("assistant", "Hi there!")

        history = session_manager.get_conversation_history()
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "Hello"

    def test_log_decision(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test logging decisions."""
        session_manager.log_decision("Chose Next.js", context="Best fit for requirements")

        decisions_path = session_manager.context_dir / "decisions.md"
        assert decisions_path.exists()
        content = decisions_path.read_text()
        assert "Chose Next.js" in content
        assert "Best fit" in content

    def test_conversation_history_limit(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test conversation history respects limit."""
        # Add 150 entries
        for i in range(150):
            session_manager.log_conversation("user", f"Message {i}")

        # Should return last 100 by default
        history = session_manager.get_conversation_history(limit=100)
        assert len(history) == 100
        assert history[0].content == "Message 50"
        assert history[-1].content == "Message 149"


# Test resume after restart
class TestResume:
    """Test session resume functionality."""

    def test_persist_and_resume(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
        temp_session_dir: Path,
    ) -> None:
        """Test that session persists and can be resumed."""
        # Progress through some phases
        session_manager.start_phase(PipelinePhase.ANALYZING)
        session_manager.complete_phase(PipelinePhase.ANALYZING)
        session_manager.approve_phase(PipelinePhase.ANALYZING)
        session_manager.start_phase(PipelinePhase.PLANNING)

        # Save content
        session_manager.save_analysis("Analysis content")
        session_manager.save_plan("Plan content")

        # Simulate restart - create new manager
        new_manager = SessionManager(temp_session_dir)
        assert new_manager.has_session()

        loaded = new_manager.load_session()
        assert loaded.current_phase == PipelinePhase.PLANNING
        assert loaded.analysis.status == PhaseStatus.APPROVED

        # Content should be preserved
        assert new_manager.get_analysis() == "Analysis content"
        assert new_manager.get_plan() == "Plan content"

    def test_version_tracking(
        self,
        session_manager: SessionManager,
        initialized_session: SessionData,
    ) -> None:
        """Test version tracking across saves."""
        session_manager.start_phase(PipelinePhase.ANALYZING)
        session_manager.complete_phase(PipelinePhase.ANALYZING)
        session_manager.request_revision(PipelinePhase.ANALYZING, "Fix")
        session_manager.complete_phase(PipelinePhase.ANALYZING)
        session_manager.request_revision(PipelinePhase.ANALYZING, "Another fix")

        assert session_manager.session.total_revisions == 2
        assert session_manager.session.analysis.version == 3
