"""Base crew module defining the interface for all crews."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class CrewStatus(Enum):
    """Status of a crew execution."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CrewResult:
    """Result of a crew execution."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CrewContext:
    """Context for crew execution."""

    session_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)


class BaseCrew(ABC):
    """Abstract base class for all crews.

    All crews must inherit from this class and implement the required methods.
    """

    def __init__(self, name: str, context: CrewContext | None = None):
        self.name = name
        self.context = context or CrewContext()
        self._status = CrewStatus.IDLE
        self._error: str | None = None

    @abstractmethod
    async def execute(self, **kwargs) -> CrewResult:
        """Execute the crew's main task.

        Args:
            **kwargs: Execution parameters specific to the crew.

        Returns:
            CrewResult: The result of the execution.
        """
        pass

    @abstractmethod
    async def validate(self, **kwargs) -> tuple[bool, str | None]:
        """Validate inputs before execution.

        Args:
            **kwargs: Parameters to validate.

        Returns:
            tuple[bool, str | None]: (is_valid, error_message)
        """
        pass

    def get_status(self) -> CrewStatus:
        """Get the current status of the crew.

        Returns:
            CrewStatus: Current status.
        """
        return self._status

    def get_error(self) -> str | None:
        """Get the last error message if any.

        Returns:
            str | None: Error message or None.
        """
        return self._error

    def _set_status(self, status: CrewStatus) -> None:
        """Update crew status."""
        self._status = status

    def _set_error(self, error: str | None) -> None:
        """Set error message."""
        self._error = error

    async def health_check(self) -> dict[str, Any]:
        """Check crew health status.

        Returns:
            dict[str, Any]: Health check results.
        """
        return {
            "name": self.name,
            "status": self._status.value,
            "healthy": self._status != CrewStatus.FAILED,
            "context": {
                "session_id": self.context.session_id,
            },
        }
