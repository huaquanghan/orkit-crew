"""File output handler.

Handles output to files with rotation and append support.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import OutputHandler
from ..output import OutputFormat, OutputMessage


class FileHandler(OutputHandler):
    """Handler for file output.

    Supports appending to files, rotation, and different output formats.
    """

    def __init__(
        self,
        name: str = "file",
        filepath: str | Path = "output.log",
        append: bool = True,
        rotate: bool = False,
        max_size: int = 10 * 1024 * 1024,  # 10MB
        max_files: int = 5,
        format_as_json: bool = False,
        **config: object,
    ):
        """Initialize file handler.

        Args:
            name: Handler name
            filepath: Path to output file
            append: Whether to append or overwrite
            rotate: Whether to rotate files when max_size is reached
            max_size: Maximum file size before rotation
            max_files: Maximum number of rotated files to keep
            format_as_json: Whether to format output as JSON
            **config: Additional configuration
        """
        super().__init__(
            name,
            filepath=filepath,
            append=append,
            rotate=rotate,
            max_size=max_size,
            max_files=max_files,
            format_as_json=format_as_json,
            **config,
        )
        self.filepath = Path(filepath)
        self.append = append
        self.rotate = rotate
        self.max_size = max_size
        self.max_files = max_files
        self.format_as_json = format_as_json

        # Ensure directory exists
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def _should_rotate(self) -> bool:
        """Check if file should be rotated."""
        if not self.rotate or not self.filepath.exists():
            return False
        return self.filepath.stat().st_size >= self.max_size

    def _rotate(self) -> None:
        """Rotate log files."""
        # Remove oldest file if exists
        oldest = self.filepath.with_suffix(f".log.{self.max_files}")
        if oldest.exists():
            oldest.unlink()

        # Shift existing files
        for i in range(self.max_files - 1, 0, -1):
            old = self.filepath.with_suffix(f".log.{i}")
            new = self.filepath.with_suffix(f".log.{i + 1}")
            if old.exists():
                old.rename(new)

        # Move current file
        if self.filepath.exists():
            self.filepath.rename(self.filepath.with_suffix(".log.1"))

    def _format_message(self, message: OutputMessage) -> str:
        """Format message for file output."""
        if self.format_as_json:
            return json.dumps(message.to_dict(), ensure_ascii=False)

        # Text format with timestamp
        timestamp = datetime.fromtimestamp(message.timestamp).isoformat()
        lines = [f"[{timestamp}] [{message.status.upper()}]"]

        # Add metadata
        if message.metadata:
            meta_str = ", ".join(f"{k}={v}" for k, v in message.metadata.items())
            lines[0] += f" [{meta_str}]"

        # Add content
        content = message.content
        if message.format == OutputFormat.JSON:
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    pass
            content = json.dumps(content, indent=2, ensure_ascii=False)
        elif message.format == OutputFormat.STRUCTURED:
            content = json.dumps(content, indent=2, ensure_ascii=False)
        else:
            content = str(content)

        lines.append(content)
        lines.append("")  # Empty line separator

        return "\n".join(lines)

    def handle(self, message: OutputMessage) -> None:
        """Handle an output message to file.

        Args:
            message: The message to output
        """
        if not self._enabled:
            return

        # Check rotation
        if self._should_rotate():
            self._rotate()

        # Write to file
        mode = "a" if self.append else "w"
        with open(self.filepath, mode, encoding="utf-8") as f:
            f.write(self._format_message(message) + "\n")


class JsonFileHandler(FileHandler):
    """Handler for JSON file output.

    Writes messages as JSON Lines (JSONL) format.
    """

    def __init__(
        self,
        name: str = "json_file",
        filepath: str | Path = "output.jsonl",
        append: bool = True,
        **config: object,
    ):
        """Initialize JSON file handler.

        Args:
            name: Handler name
            filepath: Path to output file
            append: Whether to append or overwrite
            **config: Additional configuration
        """
        super().__init__(
            name=name,
            filepath=filepath,
            append=append,
            format_as_json=True,
            **config,
        )
