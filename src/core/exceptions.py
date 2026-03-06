"""Custom exceptions for Orkit Crew Gateway."""

from typing import Any


class OrkitCrewError(Exception):
    """Base exception for Orkit Crew errors."""

    def __init__(
        self,
        message: str = "An error occurred",
        code: str = "internal_error",
        details: dict[str, Any] | None = None,
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to standardized error response format."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class BadRequestError(OrkitCrewError):
    """Raised when request is invalid or malformed."""

    def __init__(
        self,
        message: str = "Bad request",
        code: str = "bad_request",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            status_code=400,
        )


class UnauthorizedError(OrkitCrewError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Unauthorized",
        code: str = "unauthorized",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            status_code=401,
        )


class ForbiddenError(OrkitCrewError):
    """Raised when user doesn't have permission."""

    def __init__(
        self,
        message: str = "Forbidden",
        code: str = "forbidden",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            status_code=403,
        )


class NotFoundError(OrkitCrewError):
    """Raised when resource is not found."""

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: str | None = None,
        message: str | None = None,
        code: str = "not_found",
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if resource_id:
            details["resource_id"] = resource_id

        msg = message or f"{resource} not found"
        if resource_id:
            msg = f"{resource} not found: {resource_id}"

        super().__init__(
            message=msg,
            code=code,
            details=details,
            status_code=404,
        )
        self.resource = resource
        self.resource_id = resource_id


class TaskNotFoundError(NotFoundError):
    """Raised when a task is not found."""

    def __init__(
        self,
        task_id: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            resource="Task",
            resource_id=task_id,
            message=message,
            code="task_not_found",
            details=details,
        )
        self.task_id = task_id


class CrewNotFoundError(NotFoundError):
    """Raised when a crew type is not found."""

    def __init__(
        self,
        crew_type: str,
        available_crews: list[str] | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if available_crews:
            details["available_crews"] = available_crews

        super().__init__(
            resource="Crew",
            resource_id=crew_type,
            message=message,
            code="crew_not_found",
            details=details,
        )
        self.crew_type = crew_type
        self.available_crews = available_crews


class ValidationError(OrkitCrewError):
    """Raised when request validation fails."""

    def __init__(
        self,
        message: str = "Validation error",
        field_errors: dict[str, str] | None = None,
        code: str = "validation_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if field_errors:
            details["field_errors"] = field_errors

        super().__init__(
            message=message,
            code=code,
            details=details,
            status_code=422,
        )
        self.field_errors = field_errors


class ConflictError(OrkitCrewError):
    """Raised when there's a conflict with current state."""

    def __init__(
        self,
        message: str = "Conflict",
        code: str = "conflict",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            status_code=409,
        )


class TaskConflictError(ConflictError):
    """Raised when task operation conflicts with current state."""

    def __init__(
        self,
        task_id: str,
        current_status: str,
        attempted_operation: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        details["task_id"] = task_id
        details["current_status"] = current_status
        details["attempted_operation"] = attempted_operation

        msg = message or (
            f"Cannot {attempted_operation} task {task_id} "
            f"with status '{current_status}'"
        )

        super().__init__(
            message=msg,
            code="task_conflict",
            details=details,
        )
        self.task_id = task_id
        self.current_status = current_status
        self.attempted_operation = attempted_operation


class InternalServerError(OrkitCrewError):
    """Raised when an unexpected server error occurs."""

    def __init__(
        self,
        message: str = "Internal server error",
        code: str = "internal_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            status_code=500,
        )


class ServiceUnavailableError(OrkitCrewError):
    """Raised when a service is temporarily unavailable."""

    def __init__(
        self,
        service: str = "Service",
        message: str | None = None,
        code: str = "service_unavailable",
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        details["service"] = service

        msg = message or f"{service} is temporarily unavailable"

        super().__init__(
            message=msg,
            code=code,
            details=details,
            status_code=503,
        )
        self.service = service


class MemoryServiceError(ServiceUnavailableError):
    """Raised when memory service is unavailable."""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            service="Memory",
            message=message or "Memory service is temporarily unavailable",
            code="memory_service_unavailable",
            details=details,
        )


class RateLimitError(OrkitCrewError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        retry_after: int | None = None,
        message: str = "Rate limit exceeded",
        code: str = "rate_limit_exceeded",
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            code=code,
            details=details,
            status_code=429,
        )
        self.retry_after = retry_after


class WebSocketError(OrkitCrewError):
    """Raised when WebSocket operation fails."""

    def __init__(
        self,
        message: str = "WebSocket error",
        code: str = "websocket_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            status_code=500,
        )


class AuthenticationError(WebSocketError):
    """Raised when WebSocket authentication fails."""

    def __init__(
        self,
        message: str = "WebSocket authentication failed",
        code: str = "websocket_auth_failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
        )
