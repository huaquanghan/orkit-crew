"""Console output handler.

Handles output to the console/terminal with pretty printing support.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from .base import OutputHandler
from ..output import OutputFormat, OutputMessage


class ConsoleHandler(OutputHandler):
    """Handler for console/terminal output.

    Supports pretty printing, colors, and different output formats.
    """

    # ANSI color codes
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
    }

    def __init__(
        self,
        name: str = "console",
        use_color: bool = True,
        indent: int = 2,
        **config: object,
    ):
        """Initialize console handler.

        Args:
            name: Handler name
            use_color: Whether to use ANSI colors
            indent: Indentation for JSON output
            **config: Additional configuration
        """
        super().__init__(name, use_color=use_color, indent=indent, **config)
        self.use_color = use_color
        self.indent = indent

    def _color(self, color: str, text: str) -> str:
        """Apply color to text if colors are enabled."""
        if self.use_color and sys.stdout.isatty():
            return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"
        return text

    def _format_status(self, status: str) -> str:
        """Format status with color."""
        colors = {
            "success": "green",
            "error": "red",
            "warning": "yellow",
            "info": "blue",
        }
        icon = {
            "success": "✓",
            "error": "✗",
            "warning": "⚠",
            "info": "ℹ",
        }.get(status, "•")

        return self._color(colors.get(status, "reset"), f"{icon} {status.upper()}")

    def _format_progress_bar(self, progress: float, width: int = 30) -> str:
        """Format a progress bar."""
        filled = int(width * progress)
        bar = "█" * filled + "░" * (width - filled)
        percentage = int(progress * 100)
        return f"[{bar}] {percentage}%"

    def _format_structured(self, content: dict[str, Any]) -> str:
        """Format structured content."""
        content_type = content.get("type")

        if content_type == "table":
            return self._format_table(content)
        elif content_type == "list":
            return self._format_list(content)
        else:
            return json.dumps(content, indent=self.indent, ensure_ascii=False)

    def _format_table(self, content: dict[str, Any]) -> str:
        """Format table content."""
        headers = content.get("headers", [])
        rows = content.get("rows", [])

        if not headers and not rows:
            return "(empty table)"

        # Calculate column widths
        all_rows = [headers] + rows if headers else rows
        col_widths = []
        for col_idx in range(len(all_rows[0]) if all_rows else 0):
            max_width = max(
                len(str(row[col_idx])) if col_idx < len(row) else 0
                for row in all_rows
            )
            col_widths.append(max_width + 2)

        lines = []

        # Header row
        if headers:
            header_row = ""
            for i, header in enumerate(headers):
                header_row += self._color("bold", str(header).ljust(col_widths[i]))
            lines.append(header_row)
            lines.append("-" * sum(col_widths))

        # Data rows
        for row in rows:
            row_str = ""
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    row_str += str(cell).ljust(col_widths[i])
            lines.append(row_str)

        return "\n".join(lines)

    def _format_list(self, content: dict[str, Any]) -> str:
        """Format list content."""
        title = content.get("title")
        items = content.get("items", [])

        lines = []
        if title:
            lines.append(self._color("bold", title))
            lines.append("")

        for i, item in enumerate(items, 1):
            if isinstance(item, dict):
                # Format dict items
                item_str = f"  {i}. "
                if "name" in item:
                    item_str += self._color("bold", str(item["name"]))
                    if "description" in item:
                        item_str += f" - {item['description']}"
                else:
                    item_str += str(item)
                lines.append(item_str)
            else:
                lines.append(f"  • {item}")

        return "\n".join(lines)

    def handle(self, message: OutputMessage) -> None:
        """Handle an output message to console.

        Args:
            message: The message to output
        """
        if not self._enabled:
            return

        output_lines = []

        # Status line
        if message.status != "success":
            output_lines.append(self._format_status(message.status))

        # Progress bar if present
        progress = message.metadata.get("progress")
        if progress is not None:
            output_lines.append(self._format_progress_bar(float(progress)))

        # Main content
        content = message.content

        if message.format == OutputFormat.JSON:
            # JSON content - pretty print
            try:
                if isinstance(content, str):
                    # Already JSON string, parse and re-format
                    parsed = json.loads(content)
                    content = json.dumps(parsed, indent=self.indent, ensure_ascii=False)
                else:
                    # Python object, convert to JSON
                    content = json.dumps(content, indent=self.indent, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass
            output_lines.append(content)

        elif message.format == OutputFormat.STRUCTURED:
            # Structured content
            if isinstance(content, dict):
                output_lines.append(self._format_structured(content))
            else:
                output_lines.append(str(content))

        elif message.format == OutputFormat.MARKDOWN:
            # Markdown content - print as-is for now
            # Could add markdown rendering in the future
            output_lines.append(str(content))

        else:
            # Text format
            output_lines.append(str(content))

        # Error details if present
        error_code = message.metadata.get("error_code")
        if error_code:
            output_lines.append(self._color("dim", f"Error Code: {error_code}"))

        details = message.metadata.get("details")
        if details:
            output_lines.append(self._color("dim", "Details:"))
            for key, value in details.items():
                output_lines.append(self._color("dim", f"  {key}: {value}"))

        # Print output
        output = "\n".join(line for line in output_lines if line)
        if output:
            print(output)
