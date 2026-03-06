"""Task State module for managing task execution states."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from .state_machine import State, StateMachine

logger = logging.getLogger(__name__)


class TaskPhase(Enum):
    """Task lifecycle phases."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskResult:
    """Result of a task execution."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    output: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "output": self.output,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskResult":
        """Create from dictionary."""
        return cls(
            success=data["success"],
            data=data.get("data"),
            error=data.get("error"),
            output=data.get("output"),
        )


@dataclass
class TaskMetadata:
    """Metadata for a task."""

    crew_type: str = "generic"  # e.g., "planning", "coding"
    priority: int = 0  # Higher = more important
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # Task IDs
    max_retries: int = 3
    custom_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "crew_type": self.crew_type,
            "priority": self.priority,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "max_retries": self.max_retries,
            "custom_data": self.custom_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskMetadata":
        """Create from dictionary."""
        return cls(
            crew_type=data.get("crew_type", "generic"),
            priority=data.get("priority", 0),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", []),
            max_retries=data.get("max_retries", 3),
            custom_data=data.get("custom_data", {}),
        )


class TaskState:
    """State manager for task execution.

    Manages task lifecycle:
    PENDING → RUNNING → COMPLETED/FAILED

    Features:
    - Progress tracking (0-100%)
    - Retry handling
    - Failure tracking
    - Integration with StateMachine
    """

    def __init__(
        self,
        task_id: str | None = None,
        description: str = "",
        metadata: TaskMetadata | None = None,
    ):
        self._task_id = task_id or str(uuid4())
        self._description = description
        self._metadata = metadata or TaskMetadata()
        self._phase = TaskPhase.PENDING
        self._state_machine = StateMachine(
            initial_state=State.IDLE,
            entity_id=self._task_id,
            entity_type="task",
        )
        self._progress = 0.0  # 0.0 to 100.0
        self._result: TaskResult | None = None
        self._retry_count = 0
        self._failures: list[dict[str, Any]] = []
        self._created_at = datetime.now(timezone.utc)
        self._started_at: datetime | None = None
        self._completed_at: datetime | None = None

    @property
    def task_id(self) -> str:
        """Get task ID."""
        return self._task_id

    @property
    def description(self) -> str:
        """Get task description."""
        return self._description

    @property
    def phase(self) -> TaskPhase:
        """Get current task phase."""
        return self._phase

    @property
    def state(self) -> State:
        """Get current state from state machine."""
        return self._state_machine.state

    @property
    def metadata(self) -> TaskMetadata:
        """Get task metadata."""
        return self._metadata

    @property
    def progress(self) -> float:
        """Get current progress (0-100)."""
        return self._progress

    @property
    def result(self) -> TaskResult | None:
        """Get task result if completed."""
        return self._result

    @property
    def retry_count(self) -> int:
        """Get number of retries attempted."""
        return self._retry_count

    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self._retry_count < self._metadata.max_retries

    @property
    def is_terminal(self) -> bool:
        """Check if task is in terminal state."""
        return self._phase in {TaskPhase.COMPLETED, TaskPhase.FAILED}

    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at

    @property
    def started_at(self) -> datetime | None:
        """Get start timestamp."""
        return self._started_at

    @property
    def completed_at(self) -> datetime | None:
        """Get completion timestamp."""
        return self._completed_at

    def start(self) -> None:
        """Start the task."""
        if self._phase != TaskPhase.PENDING:
            raise ValueError(f"Cannot start task from phase: {self._phase}")

        self._phase = TaskPhase.RUNNING
        self._started_at = datetime.now(timezone.utc)
        self._state_machine.transition_to(
            State.RUNNING,
            metadata={"action": "task_started"},
        )
        logger.debug(f"Task {self._task_id} started")

    def update_progress(self, progress: float, message: str | None = None) -> None:
        """Update task progress.

        Args:
            progress: Progress percentage (0-100).
            message: Optional progress message.
        """
        if not 0 <= progress <= 100:
            raise ValueError("Progress must be between 0 and 100")

        self._progress = progress
        metadata = {"progress": progress}
        if message:
            metadata["message"] = message

        logger.debug(f"Task {self._task_id} progress: {progress}%")

    def complete(self, result: TaskResult) -> None:
        """Mark task as completed.

        Args:
            result: Task execution result.
        """
        if self._phase != TaskPhase.RUNNING:
            raise ValueError(f"Cannot complete task from phase: {self._phase}")

        self._phase = TaskPhase.COMPLETED
        self._result = result
        self._progress = 100.0
        self._completed_at = datetime.now(timezone.utc)

        self._state_machine.transition_to(
            State.COMPLETED if result.success else State.FAILED,
            metadata={
                "action": "task_completed",
                "success": result.success,
                "has_error": result.error is not None,
            },
        )
        logger.debug(f"Task {self._task_id} completed: success={result.success}")

    def fail(self, error: str, output: str | None = None) -> None:
        """Mark task as failed.

        Args:
            error: Error message.
            output: Optional output from failed execution.
        """
        if self._phase not in {TaskPhase.PENDING, TaskPhase.RUNNING}:
            raise ValueError(f"Cannot fail task from phase: {self._phase}")

        self._phase = TaskPhase.FAILED
        self._failures.append({
            "error": error,
            "output": output,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": self._retry_count,
        })

        self._state_machine.transition_to(
            State.FAILED,
            metadata={"action": "task_failed", "error": error},
        )
        logger.error(f"Task {self._task_id} failed: {error}")

    def retry(self) -> None:
        """Retry a failed task."""
        if self._phase != TaskPhase.FAILED:
            raise ValueError("Can only retry failed tasks")

        if not self.can_retry:
            raise ValueError(f"Max retries ({self._metadata.max_retries}) exceeded")

        self._retry_count += 1
        self._phase = TaskPhase.PENDING
        self._progress = 0.0
        self._result = None

        self._state_machine.transition_to(
            State.IDLE,
            metadata={
                "action": "task_retry",
                "retry_count": self._retry_count,
                "max_retries": self._metadata.max_retries,
            },
        )
        logger.debug(f"Task {self._task_id} retry #{self._retry_count}")

    def cancel(self) -> None:
        """Cancel the task."""
        if self._phase in {TaskPhase.COMPLETED, TaskPhase.FAILED}:
            raise ValueError(f"Cannot cancel task in phase: {self._phase}")

        self._phase = TaskPhase.FAILED
        self._completed_at = datetime.now(timezone.utc)

        self._state_machine.transition_to(
            State.CANCELLED,
            metadata={"action": "task_cancelled"},
        )
        logger.debug(f"Task {self._task_id} cancelled")

    def on_state_change(self, callback, state=None):
        """Register callback for state changes.

        Args:
            callback: Function to call on state change.
            state: Specific state or None for all changes.
        """
        self._state_machine.on_state_change(callback, state)

    def get_duration(self) -> float:
        """Get task duration in seconds.

        Returns:
            float: Seconds since task started, or total duration if completed.
        """
        if self._completed_at:
            return (self._completed_at - (self._started_at or self._created_at)).total_seconds()
        if self._started_at:
            return (datetime.now(timezone.utc) - self._started_at).total_seconds()
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence.

        Returns:
            dict: Serializable representation.
        """
        return {
            "task_id": self._task_id,
            "description": self._description,
            "phase": self._phase.value,
            "state_machine": self._state_machine.to_dict(),
            "metadata": self._metadata.to_dict(),
            "progress": self._progress,
            "result": self._result.to_dict() if self._result else None,
            "retry_count": self._retry_count,
            "failures": self._failures,
            "created_at": self._created_at.isoformat(),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskState":
        """Create from dictionary.

        Args:
            data: Dictionary from to_dict().

        Returns:
            TaskState: Restored task state.
        """
        ts = cls(
            task_id=data["task_id"],
            description=data.get("description", ""),
            metadata=TaskMetadata.from_dict(data.get("metadata", {})),
        )
        ts._phase = TaskPhase(data["phase"])
        ts._state_machine = StateMachine.from_dict(data["state_machine"])
        ts._progress = data.get("progress", 0.0)
        if data.get("result"):
            ts._result = TaskResult.from_dict(data["result"])
        ts._retry_count = data.get("retry_count", 0)
        ts._failures = data.get("failures", [])
        ts._created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            ts._started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            ts._completed_at = datetime.fromisoformat(data["completed_at"])
        return ts

    def __repr__(self) -> str:
        return f"TaskState(id={self._task_id}, phase={self._phase.value}, state={self._state_machine.state.value}, progress={self._progress:.1f}%)"
