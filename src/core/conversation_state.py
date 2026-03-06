"""Conversation State module for managing chat conversation states."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from .state_machine import State, StateMachine

logger = logging.getLogger(__name__)


class ConversationPhase(Enum):
    """Conversation lifecycle phases."""

    START = "start"
    ACTIVE = "active"
    ENDED = "ended"


@dataclass
class ConversationMetadata:
    """Metadata for a conversation."""

    user_id: str | None = None
    channel: str | None = None  # e.g., "telegram", "discord"
    topic: str | None = None
    tags: list[str] = field(default_factory=list)
    custom_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "channel": self.channel,
            "topic": self.topic,
            "tags": self.tags,
            "custom_data": self.custom_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationMetadata":
        """Create from dictionary."""
        return cls(
            user_id=data.get("user_id"),
            channel=data.get("channel"),
            topic=data.get("topic"),
            tags=data.get("tags", []),
            custom_data=data.get("custom_data", {}),
        )


class ConversationState:
    """State manager for chat conversations.

    Manages conversation flow:
    START → ACTIVE → ENDED

    Features:
    - Conversation lifecycle tracking
    - Interruption and resume handling
    - Metadata storage
    - Integration with StateMachine
    """

    def __init__(
        self,
        conversation_id: str | None = None,
        metadata: ConversationMetadata | None = None,
    ):
        self._conversation_id = conversation_id or str(uuid4())
        self._metadata = metadata or ConversationMetadata()
        self._phase = ConversationPhase.START
        self._state_machine = StateMachine(
            initial_state=State.IDLE,
            entity_id=self._conversation_id,
            entity_type="conversation",
        )
        self._created_at = datetime.now(timezone.utc)
        self._last_activity = datetime.now(timezone.utc)
        self._message_count = 0
        self._interrupted_at: datetime | None = None
        self._interruption_reason: str | None = None
        self._resumed_at: datetime | None = None

    @property
    def conversation_id(self) -> str:
        """Get conversation ID."""
        return self._conversation_id

    @property
    def phase(self) -> ConversationPhase:
        """Get current conversation phase."""
        return self._phase

    @property
    def state(self) -> State:
        """Get current state from state machine."""
        return self._state_machine.state

    @property
    def metadata(self) -> ConversationMetadata:
        """Get conversation metadata."""
        return self._metadata

    @property
    def message_count(self) -> int:
        """Get number of messages in conversation."""
        return self._message_count

    @property
    def is_active(self) -> bool:
        """Check if conversation is active."""
        return self._phase == ConversationPhase.ACTIVE and self._state_machine.is_active()

    @property
    def is_ended(self) -> bool:
        """Check if conversation has ended."""
        return self._phase == ConversationPhase.ENDED

    @property
    def is_interrupted(self) -> bool:
        """Check if conversation is interrupted."""
        return self._interrupted_at is not None and self._resumed_at is None

    @property
    def last_activity(self) -> datetime:
        """Get last activity timestamp."""
        return self._last_activity

    def start(self, metadata: dict[str, Any] | None = None) -> None:
        """Start the conversation.

        Args:
            metadata: Optional metadata to update.
        """
        if self._phase != ConversationPhase.START:
            raise ValueError(f"Cannot start conversation from phase: {self._phase}")

        self._phase = ConversationPhase.ACTIVE
        self._state_machine.transition_to(
            State.RUNNING,
            metadata={"action": "conversation_started", **(metadata or {})},
        )
        self._update_activity()
        logger.debug(f"Conversation {self._conversation_id} started")

    def end(self, reason: str | None = None) -> None:
        """End the conversation.

        Args:
            reason: Optional reason for ending.
        """
        if self._phase == ConversationPhase.ENDED:
            return

        self._phase = ConversationPhase.ENDED
        self._state_machine.transition_to(
            State.COMPLETED,
            metadata={"action": "conversation_ended", "reason": reason},
        )
        logger.debug(f"Conversation {self._conversation_id} ended: {reason}")

    def interrupt(self, reason: str) -> None:
        """Interrupt the conversation.

        Args:
            reason: Reason for interruption.
        """
        if self._phase != ConversationPhase.ACTIVE:
            raise ValueError(f"Cannot interrupt conversation in phase: {self._phase}")

        self._interrupted_at = datetime.now(timezone.utc)
        self._interruption_reason = reason
        self._state_machine.transition_to(
            State.PAUSED,
            metadata={"action": "conversation_interrupted", "reason": reason},
        )
        logger.debug(f"Conversation {self._conversation_id} interrupted: {reason}")

    def resume(self) -> None:
        """Resume the conversation after interruption."""
        if not self.is_interrupted:
            raise ValueError("Conversation is not interrupted")

        self._resumed_at = datetime.now(timezone.utc)
        self._state_machine.transition_to(
            State.RUNNING,
            metadata={
                "action": "conversation_resumed",
                "interrupted_at": self._interrupted_at.isoformat() if self._interrupted_at else None,
                "resumed_at": self._resumed_at.isoformat(),
            },
        )
        self._update_activity()
        logger.debug(f"Conversation {self._conversation_id} resumed")

    def record_message(self, role: str = "user") -> None:
        """Record a message in the conversation.

        Args:
            role: Role of the message sender.
        """
        self._message_count += 1
        self._update_activity()

    def fail(self, error: str) -> None:
        """Mark conversation as failed.

        Args:
            error: Error message.
        """
        self._state_machine.transition_to(
            State.FAILED,
            metadata={"action": "conversation_failed", "error": error},
        )
        logger.error(f"Conversation {self._conversation_id} failed: {error}")

    def retry(self) -> None:
        """Retry a failed conversation."""
        if self._state_machine.state != State.FAILED:
            raise ValueError("Can only retry failed conversations")

        self._state_machine.transition_to(
            State.RUNNING,
            metadata={"action": "conversation_retry"},
        )
        self._update_activity()
        logger.debug(f"Conversation {self._conversation_id} retried")

    def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self._last_activity = datetime.now(timezone.utc)

    def get_duration(self) -> float:
        """Get conversation duration in seconds.

        Returns:
            float: Seconds since conversation started.
        """
        return (datetime.now(timezone.utc) - self._created_at).total_seconds()

    def get_idle_duration(self) -> float:
        """Get idle time since last activity.

        Returns:
            float: Seconds since last activity.
        """
        return (datetime.now(timezone.utc) - self._last_activity).total_seconds()

    def on_state_change(self, callback, state=None):
        """Register callback for state changes.

        Args:
            callback: Function to call on state change.
            state: Specific state or None for all changes.
        """
        self._state_machine.on_state_change(callback, state)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence.

        Returns:
            dict: Serializable representation.
        """
        return {
            "conversation_id": self._conversation_id,
            "phase": self._phase.value,
            "state_machine": self._state_machine.to_dict(),
            "metadata": self._metadata.to_dict(),
            "created_at": self._created_at.isoformat(),
            "last_activity": self._last_activity.isoformat(),
            "message_count": self._message_count,
            "interrupted_at": self._interrupted_at.isoformat() if self._interrupted_at else None,
            "interruption_reason": self._interruption_reason,
            "resumed_at": self._resumed_at.isoformat() if self._resumed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationState":
        """Create from dictionary.

        Args:
            data: Dictionary from to_dict().

        Returns:
            ConversationState: Restored conversation state.
        """
        cs = cls(
            conversation_id=data["conversation_id"],
            metadata=ConversationMetadata.from_dict(data.get("metadata", {})),
        )
        cs._phase = ConversationPhase(data["phase"])
        cs._state_machine = StateMachine.from_dict(data["state_machine"])
        cs._created_at = datetime.fromisoformat(data["created_at"])
        cs._last_activity = datetime.fromisoformat(data["last_activity"])
        cs._message_count = data.get("message_count", 0)
        if data.get("interrupted_at"):
            cs._interrupted_at = datetime.fromisoformat(data["interrupted_at"])
        cs._interruption_reason = data.get("interruption_reason")
        if data.get("resumed_at"):
            cs._resumed_at = datetime.fromisoformat(data["resumed_at"])
        return cs

    def __repr__(self) -> str:
        return f"ConversationState(id={self._conversation_id}, phase={self._phase.value}, state={self._state_machine.state.value})"
