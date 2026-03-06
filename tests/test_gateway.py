"""Tests for Orkit Crew Gateway components."""

import pytest
from fastapi.testclient import TestClient

from src.core.exceptions import (
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
from src.core.memory import memory_manager
from src.core.router import CouncilRouter
from src.gateway.server import create_app


# =============================================================================
# Exception Tests
# =============================================================================

class TestExceptions:
    """Test custom exception classes."""

    def test_orkitcrew_error_base(self):
        """Test base OrkitCrewError."""
        exc = OrkitCrewError(
            message="Test error",
            code="test_error",
            details={"key": "value"},
            status_code=500,
        )
        assert exc.message == "Test error"
        assert exc.code == "test_error"
        assert exc.details == {"key": "value"}
        assert exc.status_code == 500

        error_dict = exc.to_dict()
        assert error_dict["error"]["code"] == "test_error"
        assert error_dict["error"]["message"] == "Test error"
        assert error_dict["error"]["details"] == {"key": "value"}

    def test_bad_request_error(self):
        """Test BadRequestError."""
        exc = BadRequestError(message="Invalid input", details={"field": "name"})
        assert exc.status_code == 400
        assert exc.code == "bad_request"
        assert "Invalid input" in str(exc)

    def test_unauthorized_error(self):
        """Test UnauthorizedError."""
        exc = UnauthorizedError(message="Access denied")
        assert exc.status_code == 401
        assert exc.code == "unauthorized"

    def test_not_found_error(self):
        """Test NotFoundError."""
        exc = NotFoundError(resource="User", resource_id="123")
        assert exc.status_code == 404
        assert exc.resource == "User"
        assert exc.resource_id == "123"
        assert "User not found: 123" in exc.message

    def test_task_not_found_error(self):
        """Test TaskNotFoundError."""
        exc = TaskNotFoundError(task_id="task-123")
        assert exc.status_code == 404
        assert exc.task_id == "task-123"
        assert "Task not found: task-123" in exc.message

    def test_crew_not_found_error(self):
        """Test CrewNotFoundError."""
        exc = CrewNotFoundError(
            crew_type="invalid_crew",
            available_crews=["planning", "coding"],
        )
        assert exc.status_code == 404
        assert exc.crew_type == "invalid_crew"
        assert exc.available_crews == ["planning", "coding"]
        assert "available_crews" in exc.details

    def test_validation_error(self):
        """Test ValidationError."""
        field_errors = {"name": "Required field", "email": "Invalid format"}
        exc = ValidationError(message="Validation failed", field_errors=field_errors)
        assert exc.status_code == 422
        assert exc.field_errors == field_errors
        assert "field_errors" in exc.details

    def test_task_conflict_error(self):
        """Test TaskConflictError."""
        exc = TaskConflictError(
            task_id="task-123",
            current_status="completed",
            attempted_operation="cancel",
        )
        assert exc.status_code == 409
        assert exc.task_id == "task-123"
        assert exc.current_status == "completed"
        assert exc.attempted_operation == "cancel"

    def test_internal_server_error(self):
        """Test InternalServerError."""
        exc = InternalServerError(message="Something went wrong")
        assert exc.status_code == 500
        assert exc.code == "internal_error"


# =============================================================================
# Router Tests
# =============================================================================

class TestCouncilRouter:
    """Test CouncilRouter functionality."""

    def test_router_detects_coding_task(self):
        """Test that coding tasks are detected correctly."""
        router = CouncilRouter()
        assert "coding" in router.CREW_TYPES
        assert "planning" in router.CREW_TYPES

    def test_router_get_available_crews(self):
        """Test getting available crews."""
        router = CouncilRouter()
        crews = router.get_available_crews()
        assert isinstance(crews, dict)
        assert "coding" in crews
        assert "planning" in crews

    @pytest.mark.asyncio
    async def test_router_submit_task_invalid_crew(self):
        """Test submitting task with invalid crew type."""
        router = CouncilRouter()
        with pytest.raises(ValueError) as exc_info:
            await router.submit_task(
                crew_type="invalid_crew",
                description="Test task",
            )
        assert "Unknown crew type" in str(exc_info.value)


# =============================================================================
# API Route Tests
# =============================================================================

@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)


class TestAPIRoutes:
    """Test API routes."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Orkit Crew Gateway"
        assert "version" in data
        assert "docs" in data
        assert "health" in data

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "memory_stats" in data

    def test_list_crews(self, client):
        """Test listing crews."""
        response = client.get("/api/v1/crews")
        assert response.status_code == 200
        data = response.json()
        assert "crews" in data
        assert isinstance(data["crews"], dict)

    def test_submit_task_validation_error(self, client):
        """Test task submission validation error."""
        response = client.post("/api/v1/tasks", json={})
        assert response.status_code == 422
        data = response.json()
        # FastAPI returns validation errors in 'detail' field by default
        assert "detail" in data or "error" in data
        # Check that validation errors contain field information
        if "detail" in data:
            assert isinstance(data["detail"], list)
            assert len(data["detail"]) > 0

    def test_submit_task_invalid_crew(self, client):
        """Test task submission with invalid crew type."""
        response = client.post("/api/v1/tasks", json={
            "crew_type": "invalid_crew",
            "description": "Test task",
        })
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "crew_not_found"
        assert "available_crews" in data["error"]["details"]

    def test_get_task_not_found(self, client):
        """Test getting non-existent task."""
        response = client.get("/api/v1/tasks/non-existent-task")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "task_not_found"

    def test_cancel_task_not_found(self, client):
        """Test cancelling non-existent task."""
        response = client.post("/api/v1/tasks/non-existent-task/cancel")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "task_not_found"

    def test_delete_task_not_found(self, client):
        """Test deleting non-existent task."""
        response = client.delete("/api/v1/tasks/non-existent-task")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "task_not_found"

    def test_list_tasks(self, client):
        """Test listing tasks."""
        response = client.get("/api/v1/tasks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# =============================================================================
# WebSocket Tests
# =============================================================================

class TestWebSocket:
    """Test WebSocket functionality."""

    def test_websocket_connection(self, client):
        """Test WebSocket connection."""
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "client_id" in data
            assert "authenticated" in data

    def test_websocket_ping_pong(self, client):
        """Test WebSocket ping/pong."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send ping
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_websocket_authentication(self, client):
        """Test WebSocket authentication."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send authentication
            websocket.send_json({"type": "authenticate", "token": "test-token"})
            data = websocket.receive_json()
            assert data["type"] == "auth_success"
            assert "client_id" in data
            assert "user_id" in data

    def test_websocket_get_stats(self, client):
        """Test WebSocket get_stats message."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Request stats
            websocket.send_json({"type": "get_stats"})
            data = websocket.receive_json()
            assert data["type"] == "stats"
            assert "data" in data

    def test_websocket_list_crews(self, client):
        """Test WebSocket list_crews message."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Request crews list
            websocket.send_json({"type": "list_crews"})
            data = websocket.receive_json()
            assert data["type"] == "crews"
            assert "data" in data

    def test_websocket_invalid_json(self, client):
        """Test WebSocket invalid JSON handling."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send invalid JSON
            websocket.send_text("not valid json")
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert data["code"] == "invalid_json"

    def test_websocket_unknown_message_type(self, client):
        """Test WebSocket unknown message type handling."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send unknown message type
            websocket.send_json({"type": "unknown_type"})
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert data["code"] == "unknown_message_type"

    def test_websocket_subscribe_task_not_found(self, client):
        """Test WebSocket subscribe to non-existent task."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Subscribe to non-existent task
            websocket.send_json({"type": "subscribe_task", "task_id": "non-existent"})
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert data["code"] == "task_not_found"


# =============================================================================
# Memory Manager Tests
# =============================================================================

class TestMemoryManager:
    """Test MemoryManager functionality."""

    @pytest.mark.asyncio
    async def test_create_and_get_task(self):
        """Test creating and retrieving a task."""
        task = await memory_manager.create_task(
            crew_type="coding",
            description="Test task",
            metadata={"key": "value"},
        )
        assert task.crew_type == "coding"
        assert task.description == "Test task"
        assert task.metadata == {"key": "value"}
        assert task.status == "pending"

        # Retrieve task
        retrieved = await memory_manager.get_task(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id

    @pytest.mark.asyncio
    async def test_update_task(self):
        """Test updating a task."""
        task = await memory_manager.create_task(
            crew_type="planning",
            description="Test task",
        )

        updated = await memory_manager.update_task(
            task.id,
            status="running",
            result={"output": "test"},
        )
        assert updated is not None
        assert updated.status == "running"
        assert updated.result == {"output": "test"}

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test cancelling a task."""
        task = await memory_manager.create_task(
            crew_type="coding",
            description="Test task",
        )

        cancelled = await memory_manager.cancel_task(task.id)
        assert cancelled is not None
        assert cancelled.status == "cancelled"

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        """Test listing tasks."""
        # Create a task
        task = await memory_manager.create_task(
            crew_type="coding",
            description="Test task",
        )

        # List all tasks
        tasks = await memory_manager.list_tasks()
        assert isinstance(tasks, list)
        assert len(tasks) >= 1

        # List by status
        pending_tasks = await memory_manager.list_tasks(status="pending")
        assert isinstance(pending_tasks, list)

    @pytest.mark.asyncio
    async def test_delete_task(self):
        """Test deleting a task."""
        task = await memory_manager.create_task(
            crew_type="planning",
            description="Test task to delete",
        )

        deleted = await memory_manager.delete_task(task.id)
        assert deleted is True

        # Verify task is deleted
        retrieved = await memory_manager.get_task(task.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting memory manager stats."""
        stats = await memory_manager.get_stats()
        assert "total_tasks" in stats
        assert "status_breakdown" in stats
        assert "health" in stats

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        health = await memory_manager.health_check()
        assert "status" in health
        assert "services" in health
        assert "fallback_active" in health
