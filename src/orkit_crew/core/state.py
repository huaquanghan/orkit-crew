"""Task state machine for managing crew execution."""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime


class TaskState(Enum):
    """States in the task lifecycle."""
    PENDING = auto()
    ANALYZING = auto()
    ROUTING = auto()
    PLANNING = auto()
    EXECUTING = auto()
    REVIEWING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class StateTransition:
    """Record of a state transition."""
    from_state: TaskState
    to_state: TaskState
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskContext:
    """Context for a task execution."""
    task_id: str
    original_task: str
    state: TaskState = TaskState.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    transitions: List[StateTransition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    error: Optional[str] = None


class TaskStateMachine:
    """State machine for managing task execution."""
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        TaskState.PENDING: [TaskState.ANALYZING, TaskState.CANCELLED],
        TaskState.ANALYZING: [TaskState.ROUTING, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.ROUTING: [TaskState.PLANNING, TaskState.EXECUTING, TaskState.FAILED],
        TaskState.PLANNING: [TaskState.EXECUTING, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.EXECUTING: [TaskState.REVIEWING, TaskState.COMPLETED, TaskState.FAILED],
        TaskState.REVIEWING: [TaskState.EXECUTING, TaskState.COMPLETED, TaskState.FAILED],
        TaskState.COMPLETED: [],
        TaskState.FAILED: [TaskState.PENDING],  # Retry
        TaskState.CANCELLED: [TaskState.PENDING],  # Retry
    }
    
    def __init__(self):
        self._tasks: Dict[str, TaskContext] = {}
        self._callbacks: Dict[TaskState, List[Callable]] = {
            state: [] for state in TaskState
        }
    
    def create_task(self, task_id: str, original_task: str) -> TaskContext:
        """Create a new task."""
        context = TaskContext(
            task_id=task_id,
            original_task=original_task,
        )
        self._tasks[task_id] = context
        return context
    
    def get_task(self, task_id: str) -> Optional[TaskContext]:
        """Get task context by ID."""
        return self._tasks.get(task_id)
    
    def can_transition(self, task_id: str, new_state: TaskState) -> bool:
        """Check if transition is valid."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        return new_state in self.VALID_TRANSITIONS.get(task.state, [])
    
    def transition(
        self,
        task_id: str,
        new_state: TaskState,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Transition task to new state."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if not self.can_transition(task_id, new_state):
            raise ValueError(
                f"Invalid transition from {task.state.name} to {new_state.name}"
            )
        
        old_state = task.state
        task.state = new_state
        task.updated_at = datetime.utcnow()
        
        transition = StateTransition(
            from_state=old_state,
            to_state=new_state,
            timestamp=task.updated_at,
            metadata=metadata or {},
        )
        task.transitions.append(transition)
        
        # Trigger callbacks
        for callback in self._callbacks.get(new_state, []):
            try:
                callback(task)
            except Exception:
                pass  # Don't let callbacks break the state machine
        
        return True
    
    def on_state(self, state: TaskState, callback: Callable) -> None:
        """Register a callback for a state."""
        self._callbacks[state].append(callback)
    
    def complete_task(self, task_id: str, result: str) -> bool:
        """Mark task as completed with result."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.result = result
        return self.transition(task_id, TaskState.COMPLETED)
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark task as failed with error."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.error = error
        return self.transition(task_id, TaskState.FAILED, {"error": error})
    
    def get_history(self, task_id: str) -> List[StateTransition]:
        """Get transition history for a task."""
        task = self._tasks.get(task_id)
        if not task:
            return []
        return task.transitions.copy()
    
    def is_terminal(self, task_id: str) -> bool:
        """Check if task is in terminal state."""
        task = self._tasks.get(task_id)
        if not task:
            return True
        return task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)
