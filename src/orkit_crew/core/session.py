"""Session Manager - Markdown-based state tracking for PRD pipeline.

This module provides filesystem-based session management for tracking pipeline
state without requiring a database. All state is stored in JSON and Markdown files.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PipelinePhase(str, Enum):
    """Pipeline phase states."""

    INIT = "init"
    ANALYZING = "analyzing"
    ANALYSIS_REVIEW = "analysis_review"
    PLANNING = "planning"
    PLAN_REVIEW = "plan_review"
    GENERATING = "generating"
    GENERATION_REVIEW = "generation_review"
    COMPLETED = "completed"
    FAILED = "failed"


class PhaseStatus(str, Enum):
    """Status of individual phases."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"
    FAILED = "failed"


class PhaseState(BaseModel):
    """State of a single pipeline phase."""

    status: PhaseStatus = PhaseStatus.PENDING
    version: int = 1
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class SessionData(BaseModel):
    """Complete session data structure."""

    session_id: str
    prd_file: str
    project_name: str
    output_dir: str
    current_phase: PipelinePhase = PipelinePhase.INIT
    created_at: datetime
    updated_at: datetime
    analysis: PhaseState = Field(default_factory=PhaseState)
    planning: PhaseState = Field(default_factory=PhaseState)
    generation: PhaseState = Field(default_factory=PhaseState)
    total_revisions: int = 0
    generated_files: list[str] = Field(default_factory=list)


class ConversationEntry(BaseModel):
    """Single conversation entry for JSONL log."""

    timestamp: datetime
    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionManager:
    """Manages session state using filesystem storage.

    Directory structure:
        .orkit/
        ├── session.json          # Session metadata
        ├── analysis.md           # Phase 1 output
        ├── plan.md               # Phase 2 output
        ├── generation_log.md     # Phase 3 progress
        ├── reviews/              # Version history
        │   ├── analysis_v1.md
        │   ├── analysis_v2.md
        │   ├── plan_v1.md
        │   └── plan_v2.md
        └── context/
            ├── conversation.jsonl  # Conversation log
            └── decisions.md        # Key decisions
    """

    ORKIT_DIR = ".orkit"
    SESSION_FILE = "session.json"
    ANALYSIS_FILE = "analysis.md"
    PLAN_FILE = "plan.md"
    GENERATION_LOG_FILE = "generation_log.md"
    REVIEWS_DIR = "reviews"
    CONTEXT_DIR = "context"
    CONVERSATION_FILE = "conversation.jsonl"
    DECISIONS_FILE = "decisions.md"

    def __init__(self, base_dir: str | Path) -> None:
        """Initialize session manager.

        Args:
            base_dir: Base directory for the session (project root).
        """
        self.base_dir = Path(base_dir).resolve()
        self.orkit_dir = self.base_dir / self.ORKIT_DIR
        self.reviews_dir = self.orkit_dir / self.REVIEWS_DIR
        self.context_dir = self.orkit_dir / self.CONTEXT_DIR

        self._session: SessionData | None = None

    @property
    def session(self) -> SessionData | None:
        """Get current session data."""
        return self._session

    def init_session(
        self,
        prd_file: str,
        project_name: str | None = None,
        output_dir: str = "./output",
    ) -> SessionData:
        """Initialize a new session.

        Args:
            prd_file: Path to the PRD file.
            project_name: Project name (defaults to PRD project name).
            output_dir: Output directory for generated files.

        Returns:
            Created session data.
        """
        # Create directory structure
        self._ensure_directories()

        # Generate session ID
        session_id = str(uuid.uuid4())[:8]

        now = datetime.now()
        session_data = SessionData(
            session_id=session_id,
            prd_file=str(prd_file),
            project_name=project_name or f"project-{session_id}",
            output_dir=output_dir,
            current_phase=PipelinePhase.INIT,
            created_at=now,
            updated_at=now,
        )

        self._session = session_data
        self._save_session()

        return session_data

    def load_session(self) -> SessionData:
        """Load existing session from disk.

        Returns:
            Loaded session data.

        Raises:
            FileNotFoundError: If no session exists.
            ValueError: If session file is invalid.
        """
        session_path = self.orkit_dir / self.SESSION_FILE
        if not session_path.exists():
            raise FileNotFoundError(f"No session found at {session_path}")

        with open(session_path, encoding="utf-8") as f:
            data = json.load(f)

        # Convert ISO format strings back to datetime
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        for phase in ["analysis", "planning", "generation"]:
            if data.get(phase, {}).get("started_at"):
                data[phase]["started_at"] = datetime.fromisoformat(data[phase]["started_at"])
            if data.get(phase, {}).get("completed_at"):
                data[phase]["completed_at"] = datetime.fromisoformat(data[phase]["completed_at"])

        self._session = SessionData(**data)
        return self._session

    def has_session(self) -> bool:
        """Check if a session exists.

        Returns:
            True if session.json exists and is valid.
        """
        session_path = self.orkit_dir / self.SESSION_FILE
        if not session_path.exists():
            return False

        try:
            with open(session_path, encoding="utf-8") as f:
                data = json.load(f)
            return "session_id" in data and "prd_file" in data
        except (json.JSONDecodeError, KeyError):
            return False

    def start_phase(self, phase: PipelinePhase) -> None:
        """Start a pipeline phase.

        Args:
            phase: Phase to start.

        Raises:
            RuntimeError: If no session is loaded.
        """
        if not self._session:
            raise RuntimeError("No session loaded. Call load_session() or init_session() first.")

        self._session.current_phase = phase
        phase_state = self._get_phase_state(phase)
        phase_state.status = PhaseStatus.IN_PROGRESS
        phase_state.started_at = datetime.now()

        self._update_timestamp()
        self._save_session()

    def complete_phase(self, phase: PipelinePhase) -> None:
        """Mark a phase as completed.

        Args:
            phase: Phase to complete.

        Raises:
            RuntimeError: If no session is loaded.
        """
        if not self._session:
            raise RuntimeError("No session loaded.")

        phase_state = self._get_phase_state(phase)
        phase_state.status = PhaseStatus.AWAITING_REVIEW
        phase_state.completed_at = datetime.now()

        # Move to review phase
        if phase == PipelinePhase.ANALYZING:
            self._session.current_phase = PipelinePhase.ANALYSIS_REVIEW
        elif phase == PipelinePhase.PLANNING:
            self._session.current_phase = PipelinePhase.PLAN_REVIEW
        elif phase == PipelinePhase.GENERATING:
            self._session.current_phase = PipelinePhase.GENERATION_REVIEW

        self._update_timestamp()
        self._save_session()

    def approve_phase(self, phase: PipelinePhase) -> None:
        """Approve a phase and move to next.

        Args:
            phase: Phase to approve.

        Raises:
            RuntimeError: If no session is loaded.
        """
        if not self._session:
            raise RuntimeError("No session loaded.")

        phase_state = self._get_phase_state(phase)
        phase_state.status = PhaseStatus.APPROVED

        # Move to next phase
        phase_transitions: dict[PipelinePhase, PipelinePhase] = {
            PipelinePhase.ANALYZING: PipelinePhase.PLANNING,
            PipelinePhase.ANALYSIS_REVIEW: PipelinePhase.PLANNING,
            PipelinePhase.PLANNING: PipelinePhase.GENERATING,
            PipelinePhase.PLAN_REVIEW: PipelinePhase.GENERATING,
            PipelinePhase.GENERATING: PipelinePhase.COMPLETED,
            PipelinePhase.GENERATION_REVIEW: PipelinePhase.COMPLETED,
        }

        if phase in phase_transitions:
            self._session.current_phase = phase_transitions[phase]

        self._update_timestamp()
        self._save_session()

    def request_revision(self, phase: PipelinePhase, reason: str = "") -> None:
        """Request revision for a phase.

        Args:
            phase: Phase to revise.
            reason: Reason for revision.

        Raises:
            RuntimeError: If no session is loaded.
        """
        if not self._session:
            raise RuntimeError("No session loaded.")

        phase_state = self._get_phase_state(phase)
        phase_state.status = PhaseStatus.REVISION_REQUESTED
        phase_state.version += 1

        self._session.total_revisions += 1

        # Log the revision request
        self.log_decision(f"Revision requested for {phase.value}: {reason}")

        # Move back to the work phase
        phase_transitions: dict[PipelinePhase, PipelinePhase] = {
            PipelinePhase.ANALYSIS_REVIEW: PipelinePhase.ANALYZING,
            PipelinePhase.PLAN_REVIEW: PipelinePhase.PLANNING,
            PipelinePhase.GENERATION_REVIEW: PipelinePhase.GENERATING,
        }

        if phase in phase_transitions:
            self._session.current_phase = phase_transitions[phase]

        self._update_timestamp()
        self._save_session()

    def fail_phase(self, phase: PipelinePhase, error: str) -> None:
        """Mark a phase as failed.

        Args:
            phase: Phase that failed.
            error: Error message.

        Raises:
            RuntimeError: If no session is loaded.
        """
        if not self._session:
            raise RuntimeError("No session loaded.")

        phase_state = self._get_phase_state(phase)
        phase_state.status = PhaseStatus.FAILED
        phase_state.error = error

        self._session.current_phase = PipelinePhase.FAILED

        self._update_timestamp()
        self._save_session()

    def save_analysis(self, content: str) -> Path:
        """Save analysis output.

        Args:
            content: Analysis content (markdown).

        Returns:
            Path to saved file.
        """
        if not self._session:
            raise RuntimeError("No session loaded.")

        # Save current version to reviews (backup previous version)
        analysis_path = self.orkit_dir / self.ANALYSIS_FILE
        if analysis_path.exists():
            # Backup uses previous version number (current - 1)
            version = max(1, self._session.analysis.version - 1)
            backup_path = self.reviews_dir / f"analysis_v{version}.md"
            backup_path.write_text(analysis_path.read_text(), encoding="utf-8")

        # Save new content
        analysis_path.write_text(content, encoding="utf-8")

        self._update_timestamp()
        self._save_session()

        return analysis_path

    def save_plan(self, content: str) -> Path:
        """Save plan output.

        Args:
            content: Plan content (markdown).

        Returns:
            Path to saved file.
        """
        if not self._session:
            raise RuntimeError("No session loaded.")

        # Save current version to reviews (backup previous version)
        plan_path = self.orkit_dir / self.PLAN_FILE
        if plan_path.exists():
            # Backup uses previous version number (current - 1)
            version = max(1, self._session.planning.version - 1)
            backup_path = self.reviews_dir / f"plan_v{version}.md"
            backup_path.write_text(plan_path.read_text(), encoding="utf-8")

        # Save new content
        plan_path.write_text(content, encoding="utf-8")

        self._update_timestamp()
        self._save_session()

        return plan_path

    def save_generation_log(self, content: str) -> Path:
        """Save generation log.

        Args:
            content: Generation log content (markdown).

        Returns:
            Path to saved file.
        """
        if not self._session:
            raise RuntimeError("No session loaded.")

        log_path = self.orkit_dir / self.GENERATION_LOG_FILE

        # Append to log
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n---\n\n{content}")

        self._update_timestamp()
        self._save_session()

        return log_path

    def get_analysis(self) -> str:
        """Get current analysis content.

        Returns:
            Analysis content or empty string if not exists.
        """
        analysis_path = self.orkit_dir / self.ANALYSIS_FILE
        if analysis_path.exists():
            return analysis_path.read_text(encoding="utf-8")
        return ""

    def get_plan(self) -> str:
        """Get current plan content.

        Returns:
            Plan content or empty string if not exists.
        """
        plan_path = self.orkit_dir / self.PLAN_FILE
        if plan_path.exists():
            return plan_path.read_text(encoding="utf-8")
        return ""

    def add_generated_file(self, file_path: str) -> None:
        """Add a generated file to tracking.

        Args:
            file_path: Path to generated file.
        """
        if not self._session:
            raise RuntimeError("No session loaded.")

        if file_path not in self._session.generated_files:
            self._session.generated_files.append(file_path)

        self._update_timestamp()
        self._save_session()

    def log_conversation(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Log a conversation entry.

        Args:
            role: Speaker role (user, assistant, system).
            content: Conversation content.
            metadata: Optional metadata.
        """
        entry = ConversationEntry(
            timestamp=datetime.now(),
            role=role,
            content=content,
            metadata=metadata or {},
        )

        conversation_path = self.context_dir / self.CONVERSATION_FILE
        with open(conversation_path, "a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

    def log_decision(self, decision: str, context: str = "") -> None:
        """Log a key decision.

        Args:
            decision: Decision description.
            context: Additional context.
        """
        decisions_path = self.context_dir / self.DECISIONS_FILE

        timestamp = datetime.now().isoformat()
        entry = f"\n## Decision at {timestamp}\n\n{decision}\n"
        if context:
            entry += f"\n**Context:** {context}\n"

        with open(decisions_path, "a", encoding="utf-8") as f:
            f.write(entry)

        self._update_timestamp()
        if self._session:
            self._save_session()

    def get_conversation_history(self, limit: int = 100) -> list[ConversationEntry]:
        """Get conversation history.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of conversation entries.
        """
        conversation_path = self.context_dir / self.CONVERSATION_FILE
        if not conversation_path.exists():
            return []

        entries: list[ConversationEntry] = []
        with open(conversation_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                        entries.append(ConversationEntry(**data))
                    except (json.JSONDecodeError, KeyError):
                        continue

        return entries[-limit:]

    def _ensure_directories(self) -> None:
        """Create session directory structure."""
        self.orkit_dir.mkdir(parents=True, exist_ok=True)
        self.reviews_dir.mkdir(exist_ok=True)
        self.context_dir.mkdir(exist_ok=True)

    def _save_session(self) -> None:
        """Save session data to disk."""
        if not self._session:
            return

        session_path = self.orkit_dir / self.SESSION_FILE
        with open(session_path, "w", encoding="utf-8") as f:
            f.write(self._session.model_dump_json(indent=2))

    def _update_timestamp(self) -> None:
        """Update session timestamp."""
        if self._session:
            self._session.updated_at = datetime.now()

    def _get_phase_state(self, phase: PipelinePhase) -> PhaseState:
        """Get phase state for a given phase.

        Args:
            phase: Pipeline phase.

        Returns:
            Phase state object.
        """
        if not self._session:
            raise RuntimeError("No session loaded.")

        phase_map: dict[PipelinePhase, PhaseState] = {
            PipelinePhase.ANALYZING: self._session.analysis,
            PipelinePhase.ANALYSIS_REVIEW: self._session.analysis,
            PipelinePhase.PLANNING: self._session.planning,
            PipelinePhase.PLAN_REVIEW: self._session.planning,
            PipelinePhase.GENERATING: self._session.generation,
            PipelinePhase.GENERATION_REVIEW: self._session.generation,
        }

        return phase_map.get(phase, self._session.analysis)

    def get_phase_history(self, phase: str) -> list[Path]:
        """Get version history for a phase.

        Args:
            phase: Phase name (analysis, plan, generation).

        Returns:
            List of version file paths.
        """
        pattern = f"{phase}_v*.md"
        return sorted(self.reviews_dir.glob(pattern))
