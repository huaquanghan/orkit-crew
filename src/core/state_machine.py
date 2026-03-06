"""State Machine module for managing states with transitions and callbacks."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class State(Enum):
    """Core states for the state machine."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StateTransition:
    """Represents a state transition."""

    from_state: State
    to_state: State
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert transition to dictionary."""
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StateTransition":
        """Create transition from dictionary."""
        return cls(
            from_state=State(data["from_state"]),
            to_state=State(data["to_state"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


class StateMachine:
    """State machine for managing state transitions with validation.

    Features:
    - Validated state transitions
    - State history tracking
    - Callbacks for state changes
    - Persistence support
    """

    # Define valid transitions
    VALID_TRANSITIONS: dict[State, set[State]] = {
        State.IDLE: {State.RUNNING, State.CANCELLED},
        State.RUNNING: {State.PAUSED, State.COMPLETED, State.FAILED, State.CANCELLED},
        State.PAUSED: {State.RUNNING, State.CANCELLED, State.COMPLETED},
        State.COMPLETED: set(),  # Terminal state
        State.FAILED: {State.IDLE, State.RUNNING},  # Can retry (go to IDLE first)
        State.CANCELLED: set(),  # Terminal state
    }

    def __init__(
        self,
        initial_state: State = State.IDLE,
        entity_id: str | None = None,
        entity_type: str = "generic",
    ):
        self._state = initial_state
        self._entity_id = entity_id
        self._entity_type = entity_type
        self._history: list[StateTransition] = []
        self._callbacks: dict[State, list[Callable[[State, State], None]]] = {
            state: [] for state in State
        }
        self._any_state_callbacks: list[Callable[[State, State], None]] = []
        self._created_at = datetime.now(timezone.utc)
        self._updated_at = datetime.now(timezone.utc)

        # Record initial state
        self._record_transition(initial_state, initial_state, {"initial": True})

    @property
    def state(self) -> State:
        """Get current state."""
        return self._state

    @property
    def entity_id(self) -> str | None:
        """Get entity ID."""
        return self._entity_id

    @property
    def entity_type(self) -> str:
        """Get entity type."""
        return self._entity_type

    @property
    def history(self) -> list[StateTransition]:
        """Get state transition history."""
        return self._history.copy()

    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Get last update timestamp."""
        return self._updated_at

    def can_transition_to(self, new_state: State) -> bool:
        """Check if transition to new_state is valid.

        Args:
            new_state: Target state.

        Returns:
            bool: True if transition is valid.
        """
        # Same state is always valid (no-op)
        if new_state == self._state:
            return True

        valid_next_states = self.VALID_TRANSITIONS.get(self._state, set())
        return new_state in valid_next_states

    def transition_to(
        self, new_state: State, metadata: dict[str, Any] | None = None
    ) -> bool:
        """Transition to a new state.

        Args:
            new_state: Target state.
            metadata: Optional metadata for the transition.

        Returns:
            bool: True if transition was successful.

        Raises:
            ValueError: If transition is invalid.
        """
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid transition from {self._state.value} to {new_state.value}"
            )

        if new_state == self._state:
            logger.debug(f"No-op transition to same state: {new_state.value}")
            return True

        old_state = self._state
        self._state = new_state
        self._updated_at = datetime.now(timezone.utc)

        # Record transition
        self._record_transition(old_state, new_state, metadata or {})

        # Trigger callbacks
        self._trigger_callbacks(old_state, new_state)

        logger.debug(f"State transition: {old_state.value} -> {new_state.value}")
        return True

    def _record_transition(
        self, from_state: State, to_state: State, metadata: dict[str, Any]
    ) -> None:
        """Record a state transition."""
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            metadata=metadata,
        )
        self._history.append(transition)

    def _trigger_callbacks(self, old_state: State, new_state: State) -> None:
        """Trigger callbacks for state change."""
        # Trigger specific state callbacks
        for callback in self._callbacks.get(new_state, []):
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.warning(f"State callback failed: {e}")

        # Trigger any-state callbacks
        for callback in self._any_state_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.warning(f"Any-state callback failed: {e}")

    def on_state_change(
        self, callback: Callable[[State, State], None], state: State | None = None
    ) -> None:
        """Register a callback for state changes.

        Args:
            callback: Function to call on state change.
            state: Specific state to watch, or None for all changes.
        """
        if state is None:
            self._any_state_callbacks.append(callback)
        else:
            self._callbacks[state].append(callback)

    def remove_callback(
        self, callback: Callable[[State, State], None], state: State | None = None
    ) -> bool:
        """Remove a registered callback.

        Args:
            callback: The callback to remove.
            state: Specific state or None for any-state callbacks.

        Returns:
            bool: True if callback was found and removed.
        """
        if state is None:
            if callback in self._any_state_callbacks:
                self._any_state_callbacks.remove(callback)
                return True
        else:
            if callback in self._callbacks.get(state, []):
                self._callbacks[state].remove(callback)
                return True
        return False

    def is_terminal(self) -> bool:
        """Check if current state is terminal.

        Returns:
            bool: True if state is terminal (no valid transitions).
        """
        return len(self.VALID_TRANSITIONS.get(self._state, set())) == 0

    def is_active(self) -> bool:
        """Check if state machine is in an active state.

        Returns:
            bool: True if state is RUNNING or PAUSED.
        """
        return self._state in {State.RUNNING, State.PAUSED}

    def get_state_duration(self) -> float:
        """Get duration in current state (seconds).

        Returns:
            float: Seconds since last state change.
        """
        return (datetime.now(timezone.utc) - self._updated_at).total_seconds()

    def get_total_duration(self) -> float:
        """Get total duration since creation (seconds).

        Returns:
            float: Seconds since state machine creation.
        """
        return (datetime.now(timezone.utc) - self._created_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert state machine to dictionary for persistence.

        Returns:
            dict: Serializable state representation.
        """
        return {
            "state": self._state.value,
            "entity_id": self._entity_id,
            "entity_type": self._entity_type,
            "history": [t.to_dict() for t in self._history],
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StateMachine":
        """Create state machine from dictionary.

        Args:
            data: Dictionary from to_dict().

        Returns:
            StateMachine: Restored state machine.
        """
        sm = cls(
            initial_state=State(data["state"]),
            entity_id=data.get("entity_id"),
            entity_type=data.get("entity_type", "generic"),
        )
        sm._history = [StateTransition.from_dict(t) for t in data.get("history", [])]
        sm._created_at = datetime.fromisoformat(data["created_at"])
        sm._updated_at = datetime.fromisoformat(data["updated_at"])
        return sm

    def __repr__(self) -> str:
        return f"StateMachine(state={self._state.value}, entity_id={self._entity_id})"
