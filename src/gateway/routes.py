"""API Routes for Orkit Crew Gateway with comprehensive error handling."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from ..core.exceptions import (
    BadRequestError,
    CrewNotFoundError,
    InternalServerError,
    NotFoundError,
    OrkitCrewError,
    TaskConflictError,
    TaskNotFoundError,
    UnauthorizedError,
    ValidationError,
)
from ..core.memory import memory_manager
from ..core.memory_exceptions import TaskNotFoundError as MemoryTaskNotFoundError
from ..core.router import router as council_router

# API Router
api_router = APIRouter(tags=["api"])


# =============================================================================
# Error Handlers
# =============================================================================

async def orkitcrew_exception_handler(request: Request, exc: OrkitCrewError) -> JSONResponse:
    """Handle custom OrkitCrew exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def validation_exception_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    field_errors = {}
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        field_errors[field] = error["msg"]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": {
                    "field_errors": field_errors,
                },
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    error_code = "error"
    if exc.status_code == 401:
        error_code = "unauthorized"
    elif exc.status_code == 403:
        error_code = "forbidden"
    elif exc.status_code == 404:
        error_code = "not_found"
    elif exc.status_code == 400:
        error_code = "bad_request"
    elif exc.status_code == 429:
        error_code = "rate_limit_exceeded"
    elif exc.status_code >= 500:
        error_code = "internal_error"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": error_code,
                "message": exc.detail if isinstance(exc.detail, str) else "An error occurred",
                "details": {},
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    import logging
    logger = logging.getLogger(__name__)
    logger.exception(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
                "details": {},
            }
        },
    )


def register_exception_handlers(app: Any) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(OrkitCrewError, orkitcrew_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


# =============================================================================
# Pydantic Models
# =============================================================================

class TaskSubmitRequest(BaseModel):
    """Request model for submitting a task."""

    crew_type: str = Field(..., description="Type of crew to handle the task")
    description: str = Field(..., description="Task description")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


class TaskResponse(BaseModel):
    """Response model for a task."""

    id: str
    status: str
    crew_type: str
    description: str
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float
    updated_at: float
    metadata: dict[str, Any]


class CrewInfo(BaseModel):
    """Information about a crew."""

    name: str
    description: str


class CrewsResponse(BaseModel):
    """Response model for listing crews."""

    crews: dict[str, str]


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: dict[str, Any]


# =============================================================================
# Endpoints
# =============================================================================

@api_router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new task",
    description="Submit a new task to be processed by the specified crew.",
    responses={
        400: {"model": ErrorResponse, "description": "Bad request - invalid crew type"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def submit_task(request: TaskSubmitRequest) -> TaskResponse:
    """Submit a new task for processing."""
    # Validate crew type
    available_crews = council_router.get_available_crews()
    if request.crew_type not in available_crews:
        raise CrewNotFoundError(
            crew_type=request.crew_type,
            available_crews=list(available_crews.keys()),
        )

    try:
        task = await council_router.submit_task(
            crew_type=request.crew_type,
            description=request.description,
            metadata=request.metadata,
        )
        return TaskResponse(**task.to_dict())
    except ValueError as e:
        raise BadRequestError(
            message=str(e),
            code="invalid_request",
        )
    except Exception as e:
        if isinstance(e, OrkitCrewError):
            raise
        raise InternalServerError(
            message=f"Failed to submit task: {str(e)}",
            details={"original_error": str(e)},
        )


@api_router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Get task status",
    description="Get the current status and details of a task.",
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_task(task_id: str) -> TaskResponse:
    """Get task status by ID."""
    try:
        task = await memory_manager.get_task(task_id)
    except MemoryTaskNotFoundError:
        raise TaskNotFoundError(task_id=task_id)
    except Exception as e:
        raise InternalServerError(
            message=f"Failed to retrieve task: {str(e)}",
            details={"task_id": task_id},
        )

    if not task:
        raise TaskNotFoundError(task_id=task_id)

    return TaskResponse(**task.to_dict())


@api_router.post(
    "/tasks/{task_id}/cancel",
    response_model=TaskResponse,
    summary="Cancel a task",
    description="Cancel a running or pending task.",
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Task cannot be cancelled"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def cancel_task(task_id: str) -> TaskResponse:
    """Cancel a task by ID."""
    # First check if task exists
    task = await memory_manager.get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id=task_id)

    # Check if task can be cancelled
    if task.status in ("completed", "failed", "cancelled"):
        raise TaskConflictError(
            task_id=task_id,
            current_status=task.status,
            attempted_operation="cancel",
        )

    try:
        cancelled_task = await council_router.cancel_task(task_id)
        if not cancelled_task:
            raise TaskNotFoundError(task_id=task_id)
        return TaskResponse(**cancelled_task.to_dict())
    except TaskNotFoundError:
        raise
    except TaskConflictError:
        raise
    except Exception as e:
        raise InternalServerError(
            message=f"Failed to cancel task: {str(e)}",
            details={"task_id": task_id},
        )


@api_router.get(
    "/crews",
    response_model=CrewsResponse,
    summary="List available crews",
    description="Get a list of all available crew types and their descriptions.",
)
async def list_crews() -> CrewsResponse:
    """List all available crews."""
    crews = council_router.get_available_crews()
    return CrewsResponse(crews=crews)


@api_router.get(
    "/tasks",
    response_model=list[TaskResponse],
    summary="List all tasks",
    description="Get a list of all tasks, optionally filtered by status.",
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_tasks(status: str | None = None) -> list[TaskResponse]:
    """List all tasks, optionally filtered by status."""
    try:
        tasks = await memory_manager.list_tasks(status=status)
        return [TaskResponse(**task.to_dict()) for task in tasks]
    except Exception as e:
        raise InternalServerError(
            message=f"Failed to list tasks: {str(e)}",
            details={"filter_status": status},
        )


@api_router.delete(
    "/tasks/{task_id}",
    response_model=MessageResponse,
    summary="Delete a task",
    description="Delete a task by ID.",
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_task(task_id: str) -> MessageResponse:
    """Delete a task by ID."""
    # First check if task exists
    task = await memory_manager.get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id=task_id)

    try:
        deleted = await memory_manager.delete_task(task_id)
        if not deleted:
            raise TaskNotFoundError(task_id=task_id)
        return MessageResponse(message=f"Task {task_id} deleted successfully")
    except TaskNotFoundError:
        raise
    except Exception as e:
        raise InternalServerError(
            message=f"Failed to delete task: {str(e)}",
            details={"task_id": task_id},
        )
