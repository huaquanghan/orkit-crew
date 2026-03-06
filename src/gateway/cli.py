#!/usr/bin/env python3
"""CLI entry point for Orkit Crew Gateway Server."""

import argparse
import asyncio
import logging
import sys

# Add src to path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "src"))

from gateway.server import app


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Orkit Crew Gateway Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run server on default host/port
  %(prog)s --host 0.0.0.0     # Bind to all interfaces
  %(prog)s --port 8080        # Use custom port
  %(prog)s --reload           # Enable auto-reload (development)
        """,
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (default: info)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Import uvicorn here to avoid import errors if not installed
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is required. Install with: pip install uvicorn[standard]")
        sys.exit(1)

    print(f"🚀 Starting Orkit Crew Gateway Server on http://{args.host}:{args.port}")
    print(f"📚 API Documentation: http://{args.host}:{args.port}/docs")
    print(f"🔌 WebSocket Endpoint: ws://{args.host}:{args.port}/ws")
    print("Press Ctrl+C to stop")

    uvicorn.run(
        "gateway.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
