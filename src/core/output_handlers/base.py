"""Base interface for output handlers.

All output handlers must implement the OutputHandler interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..output import OutputMessage


class OutputHandler(ABC):
    """Abstract base class for output handlers.

    All output handlers must inherit from this class and implement
    the handle method.
    """

    def __init__(self, name: str, **config: object):
        """Initialize the handler.

        Args:
            name: Handler identifier
            **config: Handler-specific configuration
        """
        self.name = name
        self.config = config
        self._enabled = True

    @abstractmethod
    def handle(self, message: OutputMessage) -> None:
        """Handle an output message.

        Args:
            message: The message to handle
        """
        raise NotImplementedError

    def enable(self) -> None:
        """Enable the handler."""
        self._enabled = True

    def disable(self) -> None:
        """Disable the handler."""
        self._enabled = False

    @property
    def enabled(self) -> bool:
        """Check if handler is enabled."""
        return self._enabled

    def __call__(self, message: OutputMessage) -> None:
        """Make handler callable."""
        if self._enabled:
            self.handle(message)
