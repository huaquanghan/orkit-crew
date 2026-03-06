"""HTTP response handler.

Handles output for HTTP/API responses with proper formatting.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from .base import OutputHandler
from ..output import OutputFormat, OutputMessage


class HttpHandler(OutputHandler):
    """Handler for HTTP/API responses.

    Formats output suitable for HTTP responses with proper content types
    and status codes.
    """

    def __init__(
        self,
        name: str = "http",
        callback: Callable[[dict[str, Any]], None] | None = None,
        **config: object,
    ):
        """Initialize HTTP handler.

        Args:
            name: Handler name
            callback: Optional callback function for responses
            **config: Additional configuration
        """
        super().__init__(name, **config)
        self.callback = callback

    def _to_http_response(self, message: OutputMessage) -> dict[str, Any]:
        """Convert message to HTTP response format.

        Returns a dictionary with:
        - status_code: HTTP status code
        - content_type: Content-Type header value
        - body: Response body
        - headers: Additional headers
        """
        # Determine status code from message status
        status_codes = {
            "success": 200,
            "error": 500,
            "warning": 200,
            "info": 200,
        }
        status_code = status_codes.get(message.status, 200)

        # Override for specific error codes
        error_code = message.metadata.get("error_code")
        if error_code == "NOT_FOUND":
            status_code = 404
        elif error_code == "BAD_REQUEST":
            status_code = 400
        elif error_code == "UNAUTHORIZED":
            status_code = 401
        elif error_code == "FORBIDDEN":
            status_code = 403

        # Format body based on format type
        if message.format == OutputFormat.JSON:
            content_type = "application/json"
            if isinstance(message.content, str):
                body = message.content
            else:
                body = json.dumps(message.content, ensure_ascii=False)

        elif message.format == OutputFormat.STRUCTURED:
            content_type = "application/json"
            body = json.dumps(message.content, ensure_ascii=False)

        elif message.format == OutputFormat.MARKDOWN:
            content_type = "text/markdown"
            body = str(message.content)

        else:
            content_type = "text/plain"
            body = str(message.content)

        # Build response
        response = {
            "status_code": status_code,
            "content_type": content_type,
            "body": body,
            "headers": {
                "X-Response-Status": message.status,
            },
        }

        # Add error code header if present
        if error_code:
            response["headers"]["X-Error-Code"] = error_code

        # Add progress header if present
        progress = message.metadata.get("progress")
        if progress is not None:
            response["headers"]["X-Progress"] = str(progress)

        return response

    def handle(self, message: OutputMessage) -> None:
        """Handle an output message for HTTP response.

        Args:
            message: The message to output
        """
        if not self._enabled:
            return

        response = self._to_http_response(message)

        if self.callback:
            self.callback(response)

    def create_fastapi_response(
        self, message: OutputMessage
    ) -> tuple[Any, int, dict[str, str]]:
        """Create a FastAPI-compatible response tuple.

        Returns (content, status_code, headers) tuple suitable for
        FastAPI's JSONResponse or plain Response.

        Args:
            message: The message to convert

        Returns:
            Tuple of (body, status_code, headers)
        """
        response = self._to_http_response(message)
        headers = response["headers"]
        headers["Content-Type"] = response["content_type"]

        # Parse body for JSON responses
        if response["content_type"] == "application/json":
            try:
                body = json.loads(response["body"])
            except json.JSONDecodeError:
                body = response["body"]
        else:
            body = response["body"]

        return body, response["status_code"], headers


class JsonApiHandler(HttpHandler):
    """Handler for JSON API responses.

    Formats output according to JSON:API specification.
    """

    def _to_http_response(self, message: OutputMessage) -> dict[str, Any]:
        """Convert message to JSON:API format."""
        # Get base response
        response = super()._to_http_response(message)

        # Build JSON:API structure
        jsonapi_response: dict[str, Any] = {
            "jsonapi": {"version": "1.0"},
            "meta": {
                "timestamp": message.timestamp,
                "status": message.status,
            },
        }

        # Add data or error
        if message.status == "error":
            jsonapi_response["errors"] = [{
                "status": str(response["status_code"]),
                "title": str(message.content),
                "detail": message.metadata.get("details", {}),
            }]
            if message.metadata.get("error_code"):
                jsonapi_response["errors"][0]["code"] = message.metadata["error_code"]
        else:
            jsonapi_response["data"] = {
                "type": "output",
                "attributes": {
                    "content": message.content,
                    "format": message.format.value,
                },
            }
            if message.metadata:
                jsonapi_response["data"]["meta"] = message.metadata

        response["body"] = json.dumps(jsonapi_response, ensure_ascii=False)
        response["content_type"] = "application/vnd.api+json"

        return response
