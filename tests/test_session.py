"""Tests for Session Manager."""

import json
import pytest
from datetime import datetime
from pathlib import Path

from orkit_crew.core.session import (
    ConversationEntry,
    PhaseStatus,
    PipelinePhase,
    SessionManager,
)


class TestSessionManager:
    """Test Session Manager functionality."""

    def test_init_session_creates_directory_structure(self, tmp_path: Path) -> None:
        """Test that init_session creates .orkit directory structure."""
        manager = SessionManager(tmp_path)
        session = manager.init_session(
            prd_file="test.prd.md",
            project_name="test-project",
        )

        # Check directories exist
        assert (tmp_path / ".orkit").exists()
        assert (tmp_path / ".orkit" / "reviews").exists()
        assert (tmp_path / ".orkit" / "context").exists()

        # Check session file exists
        assert (tmp_path / ".orkit" / "session.json").exists()

        # Check session data
        assert session.session_id is not None
        assert session.prd_file == "test.prd.md"
        assert session.project_name == "test-project"
        assert session.current_phase == PipelinePhase.INIT

    def test_session_json_valid(self, tmp_path: Path) -> None:
        """Test that session.json contains valid JSON with all fields."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        session_path = tmp_path / ".orkit" / "session.json"
        with open(session_path) as f:
            data = json.load(f)

        # Check all required fields
        assert "session_id" in data
        assert "prd_file" in data
        assert "project_name" in data
        assert "output_dir" in data
        assert "current_phase" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "analysis" in data
        assert "planning" in data
        assert "generation" in data
        assert "total_revisions" in data
        assert "generated_files" in data

    def test_phase_transitions(self, tmp_path: Path) -> None:
        """Test phase transitions work correctly."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        # Start analyzing
        manager.start_phase(PipelinePhase.ANALYZING)
        assert manager.session.current_phase == PipelinePhase.ANALYZING
        assert manager.session.analysis.status == PhaseStatus.IN_PROGRESS
        assert manager.session.analysis.started_at is not None

        # Complete analysis
        manager.complete_phase(PipelinePhase.ANALYZING)
        assert manager.session.current_phase == PipelinePhase.ANALYSIS_REVIEW
        assert manager.session.analysis.status == PhaseStatus.AWAITING_REVIEW
        assert manager.session.analysis.completed_at is not None

        # Approve analysis and move to planning
        manager.approve_phase(PipelinePhase.ANALYZING)
        assert manager.session.current_phase == PipelinePhase.PLANNING
        assert manager.session.analysis.status == PhaseStatus.APPROVED

    def test_save_analysis(self, tmp_path: Path) -> None:
        """Test save_analysis writes to .orkit/analysis.md."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        content = "# Analysis\n\nThis is the analysis."
        path = manager.save_analysis(content)

        assert path.exists()
        assert path.read_text() == content
        assert (tmp_path / ".orkit" / "analysis.md").exists()

    def test_save_plan(self, tmp_path: Path) -> None:
        """Test save_plan writes to .orkit/plan.md."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        content = "# Plan\n\nThis is the plan."
        path = manager.save_plan(content)

        assert path.exists()
        assert path.read_text() == content
        assert (tmp_path / ".orkit" / "plan.md").exists()

    def test_version_tracking(self, tmp_path: Path) -> None:
        """Test that each save creates version backup."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        # Save first version (version 1)
        manager.save_analysis("# Analysis v1")

        # Request revision to increment version to 2
        manager.request_revision(PipelinePhase.ANALYZING, "Need changes")

        # Save second version (backup will be v1 since current is now v2)
        manager.save_analysis("# Analysis v2")

        # Check backup exists (v1 backup created when saving v2)
        backup_path = tmp_path / ".orkit" / "reviews" / "analysis_v1.md"
        assert backup_path.exists()
        assert backup_path.read_text() == "# Analysis v1"

        # Check current version
        current_path = tmp_path / ".orkit" / "analysis.md"
        assert current_path.read_text() == "# Analysis v2"

    def test_request_revision_increments_version(self, tmp_path: Path) -> None:
        """Test that request_revision increments version counter."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        initial_version = manager.session.analysis.version
        initial_revisions = manager.session.total_revisions

        manager.request_revision(PipelinePhase.ANALYZING, "Need changes")

        assert manager.session.analysis.version == initial_version + 1
        assert manager.session.total_revisions == initial_revisions + 1

    def test_log_conversation_appends_jsonl(self, tmp_path: Path) -> None:
        """Test that log_conversation appends to JSONL file."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        manager.log_conversation("user", "Hello", {"key": "value"})
        manager.log_conversation("assistant", "Hi there")

        conversation_path = tmp_path / ".orkit" / "context" / "conversation.jsonl"
        assert conversation_path.exists()

        # Read and verify
        with open(conversation_path) as f:
            lines = f.readlines()

        assert len(lines) == 2

        entry1 = json.loads(lines[0])
        assert entry1["role"] == "user"
        assert entry1["content"] == "Hello"
        assert entry1["metadata"] == {"key": "value"}

        entry2 = json.loads(lines[1])
        assert entry2["role"] == "assistant"
        assert entry2["content"] == "Hi there"

    def test_load_session_restores_state(self, tmp_path: Path) -> None:
        """Test that load_session correctly restores state from disk."""
        # Create and modify session
        manager1 = SessionManager(tmp_path)
        manager1.init_session(prd_file="test.prd.md", project_name="my-project")
        manager1.start_phase(PipelinePhase.ANALYZING)
        manager1.add_generated_file("src/app.tsx")

        # Load in new manager instance
        manager2 = SessionManager(tmp_path)
        session = manager2.load_session()

        assert session.prd_file == "test.prd.md"
        assert session.project_name == "my-project"
        assert session.current_phase == PipelinePhase.ANALYZING
        assert session.analysis.status == PhaseStatus.IN_PROGRESS
        assert "src/app.tsx" in session.generated_files

    def test_has_session_returns_correct_value(self, tmp_path: Path) -> None:
        """Test has_session returns True/False correctly."""
        manager = SessionManager(tmp_path)

        # No session yet
        assert manager.has_session() is False

        # Create session
        manager.init_session(prd_file="test.prd.md")
        assert manager.has_session() is True

        # Corrupt session file
        session_path = tmp_path / ".orkit" / "session.json"
        session_path.write_text("invalid json")
        assert manager.has_session() is False

    def test_save_generation_log(self, tmp_path: Path) -> None:
        """Test save_generation_log appends to log file."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        manager.save_generation_log("Generated file 1")
        manager.save_generation_log("Generated file 2")

        log_path = tmp_path / ".orkit" / "generation_log.md"
        assert log_path.exists()

        content = log_path.read_text()
        assert "Generated file 1" in content
        assert "Generated file 2" in content

    def test_get_analysis_and_plan(self, tmp_path: Path) -> None:
        """Test get_analysis and get_plan methods."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        # Empty when no files
        assert manager.get_analysis() == ""
        assert manager.get_plan() == ""

        # Save and retrieve
        manager.save_analysis("# Analysis content")
        manager.save_plan("# Plan content")

        assert manager.get_analysis() == "# Analysis content"
        assert manager.get_plan() == "# Plan content"

    def test_log_decision(self, tmp_path: Path) -> None:
        """Test log_decision appends to decisions file."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        manager.log_decision("Use TypeScript", "Team decided on TS")

        decisions_path = tmp_path / ".orkit" / "context" / "decisions.md"
        assert decisions_path.exists()

        content = decisions_path.read_text()
        assert "Use TypeScript" in content
        assert "Team decided on TS" in content

    def test_get_conversation_history(self, tmp_path: Path) -> None:
        """Test get_conversation_history returns recent entries."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        # Add entries
        for i in range(5):
            manager.log_conversation("user", f"Message {i}")

        # Get history
        history = manager.get_conversation_history(limit=3)
        assert len(history) == 3
        assert history[0].content == "Message 2"
        assert history[2].content == "Message 4"

    def test_fail_phase(self, tmp_path: Path) -> None:
        """Test fail_phase marks phase as failed."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        manager.start_phase(PipelinePhase.ANALYZING)
        manager.fail_phase(PipelinePhase.ANALYZING, "Analysis failed due to error")

        assert manager.session.analysis.status == PhaseStatus.FAILED
        assert manager.session.analysis.error == "Analysis failed due to error"
        assert manager.session.current_phase == PipelinePhase.FAILED

    def test_add_generated_file(self, tmp_path: Path) -> None:
        """Test add_generated_file tracks files."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        manager.add_generated_file("src/app.tsx")
        manager.add_generated_file("src/page.tsx")
        manager.add_generated_file("src/app.tsx")  # Duplicate, should not add

        assert len(manager.session.generated_files) == 2
        assert "src/app.tsx" in manager.session.generated_files
        assert "src/page.tsx" in manager.session.generated_files

    def test_no_session_errors(self, tmp_path: Path) -> None:
        """Test that operations fail gracefully without session."""
        manager = SessionManager(tmp_path)

        with pytest.raises(RuntimeError, match="No session loaded"):
            manager.start_phase(PipelinePhase.ANALYZING)

        with pytest.raises(RuntimeError, match="No session loaded"):
            manager.save_analysis("content")

    def test_load_session_not_found(self, tmp_path: Path) -> None:
        """Test load_session raises FileNotFoundError."""
        manager = SessionManager(tmp_path)

        with pytest.raises(FileNotFoundError):
            manager.load_session()

    def test_session_survives_restart(self, tmp_path: Path) -> None:
        """Test that session survives process restart."""
        # First "process"
        manager1 = SessionManager(tmp_path)
        manager1.init_session(prd_file="test.prd.md", project_name="survivor")
        manager1.start_phase(PipelinePhase.ANALYZING)
        manager1.save_analysis("# Analysis")

        # Second "process" - new manager instance
        manager2 = SessionManager(tmp_path)
        assert manager2.has_session() is True

        session = manager2.load_session()
        assert session.project_name == "survivor"
        assert session.current_phase == PipelinePhase.ANALYZING
        assert manager2.get_analysis() == "# Analysis"

    def test_get_phase_history(self, tmp_path: Path) -> None:
        """Test get_phase_history returns version files."""
        manager = SessionManager(tmp_path)
        manager.init_session(prd_file="test.prd.md")

        # Create some versions
        (tmp_path / ".orkit" / "reviews" / "analysis_v1.md").write_text("v1")
        (tmp_path / ".orkit" / "reviews" / "analysis_v2.md").write_text("v2")
        (tmp_path / ".orkit" / "reviews" / "plan_v1.md").write_text("plan")

        history = manager.get_phase_history("analysis")
        assert len(history) == 2
        assert history[0].name == "analysis_v1.md"
        assert history[1].name == "analysis_v2.md"
