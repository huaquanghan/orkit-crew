"""Output Layer for formatting and sending responses.

This module provides the OutputFormatter class for formatting different output types
and a registry for output handlers.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar


class OutputFormat(Enum):
    """Supported output formats."""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    STRUCTURED = "structured"


@dataclass
class OutputMessage:
    """A structured output message.

    Attributes:
        content: The main content of the message
        format: The format type
        metadata: Additional metadata for the message
        status: Status of the message (success, error, info, warning)
        timestamp: Unix timestamp
    """

    content: Any
    format: OutputFormat = OutputFormat.TEXT
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "success"  # success, error, info, warning
    timestamp: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "content": self.content,
            "format": self.format.value,
            "metadata": self.metadata,
            "status": self.status,
            "timestamp": self.timestamp,
        }


T = TypeVar("T")


class OutputFormatter:
    """Formatter for different output types.

    Provides methods to format content as text, JSON, markdown, or structured data.
    """

    def __init__(self, indent: int = 2, use_color: bool = True):
        """Initialize the formatter.

        Args:
            indent: Indentation level for JSON output
            use_color: Whether to use ANSI colors in terminal output
        """
        self.indent = indent
        self.use_color = use_color

    def format_text(self, content: str, **metadata: Any) -> OutputMessage:
        """Format content as plain text.

        Args:
            content: The text content
            **metadata: Additional metadata

        Returns:
            OutputMessage with text format
        """
        return OutputMessage(
            content=content,
            format=OutputFormat.TEXT,
            metadata=metadata,
        )

    def format_json(
        self, data: Any, pretty: bool = True, **metadata: Any
    ) -> OutputMessage:
        """Format data as JSON.

        Args:
            data: The data to format (will be serialized to JSON)
            pretty: Whether to pretty-print the JSON
            **metadata: Additional metadata

        Returns:
            OutputMessage with JSON format
        """
        try:
            if pretty:
                content = json.dumps(data, indent=self.indent, ensure_ascii=False)
            else:
                content = json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            content = json.dumps({"error": f"Failed to serialize: {e}"})

        return OutputMessage(
            content=content,
            format=OutputFormat.JSON,
            metadata=metadata,
        )

    def format_markdown(self, content: str, **metadata: Any) -> OutputMessage:
        """Format content as Markdown.

        Args:
            content: The markdown content
            **metadata: Additional metadata

        Returns:
            OutputMessage with markdown format
        """
        return OutputMessage(
            content=content,
            format=OutputFormat.MARKDOWN,
            metadata=metadata,
        )

    def format_structured(
        self, data: dict[str, Any], **metadata: Any
    ) -> OutputMessage:
        """Format data as structured output.

        Args:
            data: Dictionary with structured data
            **metadata: Additional metadata

        Returns:
            OutputMessage with structured format
        """
        return OutputMessage(
            content=data,
            format=OutputFormat.STRUCTURED,
            metadata=metadata,
        )

    def format_error(
        self, message: str, error_code: str | None = None, details: dict[str, Any] | None = None
    ) -> OutputMessage:
        """Format an error message.

        Args:
            message: The error message
            error_code: Optional error code
            details: Optional error details

        Returns:
            OutputMessage with error status
        """
        metadata = {"error_code": error_code} if error_code else {}
        if details:
            metadata["details"] = details

        return OutputMessage(
            content=message,
            format=OutputFormat.TEXT,
            metadata=metadata,
            status="error",
        )

    def format_success(
        self, message: str, data: dict[str, Any] | None = None
    ) -> OutputMessage:
        """Format a success message.

        Args:
            message: The success message
            data: Optional additional data

        Returns:
            OutputMessage with success status
        """
        metadata = data if data else {}

        return OutputMessage(
            content=message,
            format=OutputFormat.TEXT,
            metadata=metadata,
            status="success",
        )

    def format_progress(
        self, message: str, progress: float, **metadata: Any
    ) -> OutputMessage:
        """Format a progress update.

        Args:
            message: Progress message
            progress: Progress value between 0.0 and 1.0
            **metadata: Additional metadata

        Returns:
            OutputMessage with progress info
        """
        meta = {"progress": max(0.0, min(1.0, progress))}
        meta.update(metadata)

        return OutputMessage(
            content=message,
            format=OutputFormat.TEXT,
            metadata=meta,
            status="info",
        )

    def format_table(
        self, headers: list[str], rows: list[list[Any]], **metadata: Any
    ) -> OutputMessage:
        """Format data as a table.

        Args:
            headers: Column headers
            rows: Table rows
            **metadata: Additional metadata

        Returns:
            OutputMessage with structured table data
        """
        data = {
            "type": "table",
            "headers": headers,
            "rows": rows,
        }

        return OutputMessage(
            content=data,
            format=OutputFormat.STRUCTURED,
            metadata=metadata,
        )

    def format_list(
        self, items: list[Any], title: str | None = None, **metadata: Any
    ) -> OutputMessage:
        """Format a list of items.

        Args:
            items: List of items
            title: Optional title for the list
            **metadata: Additional metadata

        Returns:
            OutputMessage with structured list data
        """
        data: dict[str, Any] = {"type": "list", "items": items}
        if title:
            data["title"] = title

        return OutputMessage(
            content=data,
            format=OutputFormat.STRUCTURED,
            metadata=metadata,
        )


class OutputRegistry:
    """Registry for output handlers.

    Manages a collection of output handlers that can be used to send
    formatted output to different destinations.
    """

    def __init__(self):
        self._handlers: dict[str, Callable[[OutputMessage], None]] = {}
        self._formatter = OutputFormatter()

    def register(
        self, name: str, handler: Callable[[OutputMessage], None]
    ) -> None:
        """Register an output handler.

        Args:
            name: Handler name
            handler: Callable that accepts an OutputMessage
        """
        self._handlers[name] = handler

    def unregister(self, name: str) -> None:
        """Unregister an output handler.

        Args:
            name: Handler name
        """
        self._handlers.pop(name, None)

    def get_handler(self, name: str) -> Callable[[OutputMessage], None] | None:
        """Get a registered handler by name.

        Args:
            name: Handler name

        Returns:
            The handler if found, None otherwise
        """
        return self._handlers.get(name)

    def send(self, message: OutputMessage, handler_name: str | None = None) -> None:
        """Send a message using the specified or all handlers.

        Args:
            message: The message to send
            handler_name: Specific handler to use, or None to use all
        """
        if handler_name:
            handler = self._handlers.get(handler_name)
            if handler:
                handler(message)
        else:
            for handler in self._handlers.values():
                handler(message)

    @property
    def formatter(self) -> OutputFormatter:
        """Get the default formatter."""
        return self._formatter

    @property
    def handlers(self) -> list[str]:
        """Get list of registered handler names."""
        return list(self._handlers.keys())


# Global registry instance
output_registry = OutputRegistry()
