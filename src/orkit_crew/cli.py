#!/usr/bin/env python3
"""CLI client for Orkit Crew Gateway Server.

This CLI communicates with the Gateway API instead of being a direct entry point.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

# Default Gateway URL
DEFAULT_GATEWAY_URL = "http://localhost:8000"

# Color codes for terminal output
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "cyan": "\033[96m",
}


def colorize(text: str, color: str) -> str:
    """Apply color to text if terminal supports it."""
    if sys.stdout.isatty():
        return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"
    return text


def get_gateway_url() -> str:
    """Get Gateway URL from environment or use default."""
    return os.environ.get("ORKIT_GATEWAY_URL", DEFAULT_GATEWAY_URL)


def handle_api_error(response: httpx.Response) -> None:
    """Handle API error responses."""
    try:
        data = response.json()
        detail = data.get("detail", "Unknown error")
    except Exception:
        detail = response.text or "Unknown error"

    error_msg = f"API Error ({response.status_code}): {detail}"
    print(colorize(error_msg, "red"), file=sys.stderr)


def handle_connection_error(error: Exception) -> None:
    """Handle connection errors to Gateway."""
    url = get_gateway_url()
    error_msg = f"""
{colorize('❌ Cannot connect to Gateway', 'red')}

Gateway URL: {url}

Possible solutions:
1. Start the Gateway server: {colorize('orkit serve', 'cyan')}
2. Check if Gateway is running on the correct host/port
3. Set ORKIT_GATEWAY_URL environment variable if Gateway is on a different URL

Example:
    export ORKIT_GATEWAY_URL=http://localhost:8000
"""
    print(error_msg, file=sys.stderr)


def format_task(task: dict[str, Any]) -> str:
    """Format a task for display."""
    status_colors = {
        "pending": "yellow",
        "running": "blue",
        "completed": "green",
        "failed": "red",
        "cancelled": "yellow",
    }

    status = task.get("status", "unknown")
    status_color = status_colors.get(status, "reset")

    lines = [
        f"{colorize('Task ID:', 'bold')} {task.get('id')}",
        f"{colorize('Status:', 'bold')} {colorize(status.upper(), status_color)}",
        f"{colorize('Crew:', 'bold')} {task.get('crew_type')}",
        f"{colorize('Description:', 'bold')} {task.get('description')}",
    ]

    if task.get("result"):
        lines.append(f"{colorize('Result:', 'bold')} {task.get('result')}")

    if task.get("error"):
        lines.append(f"{colorize('Error:', 'red')} {task.get('error')}")

    return "\n".join(lines)


def cmd_task(args: argparse.Namespace) -> int:
    """Submit a new task."""
    url = get_gateway_url()

    payload = {
        "crew_type": args.crew,
        "description": args.description,
        "metadata": {},
    }

    try:
        with httpx.Client() as client:
            response = client.post(f"{url}/api/v1/tasks", json=payload)

        if response.status_code == 201:
            data = response.json()
            print(colorize("✅ Task submitted successfully!", "green"))
            print()
            print(format_task(data))
            return 0
        else:
            handle_api_error(response)
            return 1

    except httpx.ConnectError as e:
        handle_connection_error(e)
        return 1
    except Exception as e:
        print(colorize(f"Error: {e}", "red"), file=sys.stderr)
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Get task status."""
    url = get_gateway_url()
    task_id = args.task_id

    try:
        with httpx.Client() as client:
            response = client.get(f"{url}/api/v1/tasks/{task_id}")

        if response.status_code == 200:
            data = response.json()
            print(format_task(data))
            return 0
        elif response.status_code == 404:
            print(colorize(f"❌ Task not found: {task_id}", "red"), file=sys.stderr)
            return 1
        else:
            handle_api_error(response)
            return 1

    except httpx.ConnectError as e:
        handle_connection_error(e)
        return 1
    except Exception as e:
        print(colorize(f"Error: {e}", "red"), file=sys.stderr)
        return 1


def cmd_cancel(args: argparse.Namespace) -> int:
    """Cancel a task."""
    url = get_gateway_url()
    task_id = args.task_id

    try:
        with httpx.Client() as client:
            response = client.post(f"{url}/api/v1/tasks/{task_id}/cancel")

        if response.status_code == 200:
            data = response.json()
            print(colorize("✅ Task cancelled successfully!", "green"))
            print()
            print(format_task(data))
            return 0
        elif response.status_code == 404:
            print(colorize(f"❌ Task not found: {task_id}", "red"), file=sys.stderr)
            return 1
        else:
            handle_api_error(response)
            return 1

    except httpx.ConnectError as e:
        handle_connection_error(e)
        return 1
    except Exception as e:
        print(colorize(f"Error: {e}", "red"), file=sys.stderr)
        return 1


def cmd_crews(args: argparse.Namespace) -> int:
    """List available crews."""
    url = get_gateway_url()

    try:
        with httpx.Client() as client:
            response = client.get(f"{url}/api/v1/crews")

        if response.status_code == 200:
            data = response.json()
            crews = data.get("crews", {})

            print(colorize("Available Crews:", "bold"))
            print()

            for crew_name, description in crews.items():
                print(f"  {colorize('•', 'cyan')} {colorize(crew_name, 'bold')}: {description}")

            return 0
        else:
            handle_api_error(response)
            return 1

    except httpx.ConnectError as e:
        handle_connection_error(e)
        return 1
    except Exception as e:
        print(colorize(f"Error: {e}", "red"), file=sys.stderr)
        return 1


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the Gateway server."""
    import subprocess

    # Get the path to the gateway CLI
    import pathlib

    gateway_cli = pathlib.Path(__file__).parent.parent / "gateway" / "cli.py"

    cmd = [
        sys.executable,
        str(gateway_cli),
        "--host", args.host,
        "--port", str(args.port),
        "--log-level", args.log_level,
    ]

    if args.reload:
        cmd.append("--reload")

    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        print("\n👋 Gateway server stopped")
        return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="orkit",
        description="Orkit Crew CLI - Multi-Agent AI System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Environment Variables:
  ORKIT_GATEWAY_URL    Gateway server URL (default: {DEFAULT_GATEWAY_URL})

Examples:
  %(prog)s task "Plan a marketing campaign" --crew planning
  %(prog)s status <task_id>
  %(prog)s cancel <task_id>
  %(prog)s crews
  %(prog)s serve
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # task command
    task_parser = subparsers.add_parser(
        "task",
        help="Submit a new task",
        description="Submit a new task to be processed by a crew.",
    )
    task_parser.add_argument(
        "description",
        help="Task description",
    )
    task_parser.add_argument(
        "--crew",
        default="planning",
        choices=["planning", "coding"],
        help="Crew type to handle the task (default: planning)",
    )
    task_parser.set_defaults(func=cmd_task)

    # status command
    status_parser = subparsers.add_parser(
        "status",
        help="Get task status",
        description="Get the current status of a task.",
    )
    status_parser.add_argument(
        "task_id",
        help="Task ID",
    )
    status_parser.set_defaults(func=cmd_status)

    # cancel command
    cancel_parser = subparsers.add_parser(
        "cancel",
        help="Cancel a task",
        description="Cancel a running or pending task.",
    )
    cancel_parser.add_argument(
        "task_id",
        help="Task ID",
    )
    cancel_parser.set_defaults(func=cmd_cancel)

    # crews command
    crews_parser = subparsers.add_parser(
        "crews",
        help="List available crews",
        description="List all available crew types.",
    )
    crews_parser.set_defaults(func=cmd_crews)

    # serve command
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start Gateway server",
        description="Start the Orkit Crew Gateway server.",
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    serve_parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (default: info)",
    )
    serve_parser.set_defaults(func=cmd_serve)

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
