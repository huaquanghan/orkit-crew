"""API Routes for Orkit Crew Gateway."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..core.memory import memory_manager
from ..core.router import router as council_router

# API Router
api_router = APIRouter(tags=["api"])


# Pydantic Models
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


# Endpoints
@api_router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new task",
    description="Submit a new task to be processed by the specified crew.",
)
async def submit_task(request: TaskSubmitRequest) -> TaskResponse:
    """Submit a new task for processing."""
    try:
        task = await council_router.submit_task(
            crew_type=request.crew_type,
            description=request.description,
            metadata=request.metadata,
        )
        return TaskResponse(**task.to_dict())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {str(e)}",
        )


@api_router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Get task status",
    description="Get the current status and details of a task.",
)
async def get_task(task_id: str) -> TaskResponse:
    """Get task status by ID."""
    task = await memory_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return TaskResponse(**task.to_dict())


@api_router.post(
    "/tasks/{task_id}/cancel",
    response_model=TaskResponse,
    summary="Cancel a task",
    description="Cancel a running or pending task.",
)
async def cancel_task(task_id: str) -> TaskResponse:
    """Cancel a task by ID."""
    task = await council_router.cancel_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return TaskResponse(**task.to_dict())


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
