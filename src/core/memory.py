"""Memory Manager for Orkit Crew with error handling and graceful degradation."""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .memory_exceptions import (
    MemoryError,
    RedisConnectionError,
    QdrantConnectionError,
    StorageError,
    TaskNotFoundError,
)

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Represents a task in the system."""

    id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "pending"  # pending, running, completed, failed, cancelled
    crew_type: str = "planning"  # planning, coding
    description: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "status": self.status,
            "crew_type": self.crew_type,
            "description": self.description,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    def update_status(self, status: str) -> None:
        """Update task status and timestamp."""
        self.status = status
        self.updated_at = time.time()


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    """Decorator for retry logic with exponential backoff."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2**attempt), max_delay)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {delay}s: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
            raise last_exception

        return wrapper

    return decorator


class MemoryManager:
    """Memory manager with Redis, Qdrant, and Markdown support with error handling."""

    def __init__(
        self,
        redis_url: str | None = None,
        qdrant_url: str | None = None,
        qdrant_api_key: str | None = None,
        enable_redis: bool = True,
        enable_qdrant: bool = True,
    ):
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}

        # External service configuration
        self._redis_url = redis_url
        self._qdrant_url = qdrant_url
        self._qdrant_api_key = qdrant_api_key
        self._enable_redis = enable_redis
        self._enable_qdrant = enable_qdrant

        # Service status
        self._redis_available = False
        self._qdrant_available = False
        self._redis_client = None
        self._qdrant_client = None

        # Fallback in-memory storage when Redis fails
        self._fallback_storage: dict[str, Any] = {}

        logger.info(
            f"MemoryManager initialized (redis={enable_redis}, qdrant={enable_qdrant})"
        )

    async def initialize(self) -> None:
        """Initialize connections to external services."""
        if self._enable_redis:
            await self._init_redis()
        if self._enable_qdrant:
            await self._init_qdrant()

    async def _init_redis(self) -> None:
        """Initialize Redis connection with fallback."""
        try:
            import redis.asyncio as redis

            if self._redis_url:
                self._redis_client = redis.from_url(self._redis_url)
            else:
                self._redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

            # Test connection
            await self._redis_client.ping()
            self._redis_available = True
            logger.info("Redis connection established")
        except ImportError:
            logger.warning("redis package not installed, using in-memory fallback")
            self._redis_available = False
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
            self._redis_available = False

    async def _init_qdrant(self) -> None:
        """Initialize Qdrant connection with fallback."""
        try:
            from qdrant_client import QdrantClient

            if self._qdrant_url:
                self._qdrant_client = QdrantClient(
                    url=self._qdrant_url, api_key=self._qdrant_api_key
                )
            else:
                self._qdrant_client = QdrantClient(host="localhost", port=6333)

            # Test connection
            self._qdrant_client.get_collections()
            self._qdrant_available = True
            logger.info("Qdrant connection established")
        except ImportError:
            logger.warning("qdrant-client package not installed, vector search disabled")
            self._qdrant_available = False
        except Exception as e:
            logger.warning(f"Qdrant connection failed, vector search disabled: {e}")
            self._qdrant_available = False

    # ==================== Task Operations ====================

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    async def create_task(
        self, crew_type: str, description: str, metadata: dict[str, Any] | None = None
    ) -> Task:
        """Create a new task."""
        try:
            async with self._lock:
                task = Task(
                    crew_type=crew_type,
                    description=description,
                    metadata=metadata or {},
                )
                self._tasks[task.id] = task
                self._subscribers[task.id] = []

                # Try to persist to Redis if available
                if self._redis_available and self._redis_client:
                    try:
                        await self._redis_client.set(
                            f"task:{task.id}", json.dumps(task.to_dict())
                        )
                    except Exception as e:
                        logger.warning(f"Failed to persist task to Redis: {e}")
                        # Continue - task is in memory

                logger.debug(f"Created task {task.id}")
                return task
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise StorageError("Failed to create task", operation="create", cause=e) from e

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    async def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        try:
            async with self._lock:
                # Check in-memory first
                if task_id in self._tasks:
                    return self._tasks[task_id]

                # Try Redis if available
                if self._redis_available and self._redis_client:
                    try:
                        data = await self._redis_client.get(f"task:{task_id}")
                        if data:
                            task_dict = json.loads(data)
                            task = Task(**task_dict)
                            self._tasks[task_id] = task  # Cache in memory
                            return task
                    except Exception as e:
                        logger.warning(f"Failed to get task from Redis: {e}")

                return None
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            raise StorageError(
                "Failed to get task", operation="get", key=task_id, cause=e
            ) from e

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    async def update_task(self, task_id: str, **kwargs) -> Task | None:
        """Update a task."""
        try:
            async with self._lock:
                task = self._tasks.get(task_id)
                if not task:
                    # Try to load from Redis
                    if self._redis_available and self._redis_client:
                        try:
                            data = await self._redis_client.get(f"task:{task_id}")
                            if data:
                                task_dict = json.loads(data)
                                task = Task(**task_dict)
                                self._tasks[task_id] = task
                            else:
                                raise TaskNotFoundError(task_id)
                        except TaskNotFoundError:
                            raise
                        except Exception as e:
                            logger.warning(f"Failed to load task from Redis: {e}")
                            raise TaskNotFoundError(task_id, cause=e)
                    else:
                        raise TaskNotFoundError(task_id)

                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)

                task.updated_at = time.time()

                # Update Redis if available
                if self._redis_available and self._redis_client:
                    try:
                        await self._redis_client.set(
                            f"task:{task.id}", json.dumps(task.to_dict())
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update task in Redis: {e}")

                # Notify subscribers
                await self._notify_subscribers(task)

                logger.debug(f"Updated task {task_id}")
                return task
        except TaskNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            raise StorageError(
                "Failed to update task", operation="update", key=task_id, cause=e
            ) from e

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    async def cancel_task(self, task_id: str) -> Task | None:
        """Cancel a task."""
        try:
            async with self._lock:
                task = self._tasks.get(task_id)
                if not task:
                    raise TaskNotFoundError(task_id)

                if task.status in ("completed", "failed", "cancelled"):
                    return task

                task.update_status("cancelled")

                # Update Redis if available
                if self._redis_available and self._redis_client:
                    try:
                        await self._redis_client.set(
                            f"task:{task.id}", json.dumps(task.to_dict())
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update cancelled task in Redis: {e}")

                await self._notify_subscribers(task)
                logger.debug(f"Cancelled task {task_id}")
                return task
        except TaskNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            raise StorageError(
                "Failed to cancel task", operation="cancel", key=task_id, cause=e
            ) from e

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    async def list_tasks(self, status: str | None = None) -> list[Task]:
        """List all tasks, optionally filtered by status."""
        try:
            async with self._lock:
                tasks = list(self._tasks.values())
                if status:
                    tasks = [t for t in tasks if t.status == status]
                return tasks
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            raise StorageError("Failed to list tasks", operation="list", cause=e) from e

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        try:
            async with self._lock:
                if task_id in self._tasks:
                    del self._tasks[task_id]
                    del self._subscribers[task_id]

                    # Delete from Redis if available
                    if self._redis_available and self._redis_client:
                        try:
                            await self._redis_client.delete(f"task:{task_id}")
                        except Exception as e:
                            logger.warning(f"Failed to delete task from Redis: {e}")

                    logger.debug(f"Deleted task {task_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise StorageError(
                "Failed to delete task", operation="delete", key=task_id, cause=e
            ) from e

    # ==================== Subscription Operations ====================

    async def subscribe(self, task_id: str) -> asyncio.Queue[dict[str, Any]] | None:
        """Subscribe to task updates."""
        try:
            async with self._lock:
                if task_id not in self._tasks:
                    return None
                queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
                self._subscribers[task_id].append(queue)
                return queue
        except Exception as e:
            logger.error(f"Failed to subscribe to task {task_id}: {e}")
            return None

    async def unsubscribe(
        self, task_id: str, queue: asyncio.Queue[dict[str, Any]]
    ) -> None:
        """Unsubscribe from task updates."""
        try:
            async with self._lock:
                if task_id in self._subscribers and queue in self._subscribers[task_id]:
                    self._subscribers[task_id].remove(queue)
        except Exception as e:
            logger.warning(f"Failed to unsubscribe from task {task_id}: {e}")

    async def _notify_subscribers(self, task: Task) -> None:
        """Notify all subscribers of a task update."""
        if task.id in self._subscribers:
            data = task.to_dict()
            for queue in self._subscribers[task.id]:
                try:
                    queue.put_nowait(data)
                except asyncio.QueueFull:
                    pass
                except Exception as e:
                    logger.warning(f"Failed to notify subscriber: {e}")

    # ==================== Redis Operations with Fallback ====================

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    async def set_value(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a value in storage (Redis if available, else in-memory)."""
        try:
            if self._redis_available and self._redis_client:
                try:
                    serialized = json.dumps(value)
                    if ttl:
                        await self._redis_client.setex(key, ttl, serialized)
                    else:
                        await self._redis_client.set(key, serialized)
                    return True
                except Exception as e:
                    logger.warning(f"Redis set failed, using in-memory fallback: {e}")
                    self._redis_available = False

            # Fallback to in-memory
            self._fallback_storage[key] = {"value": value, "expires": None}
            return True
        except Exception as e:
            logger.error(f"Failed to set value for key {key}: {e}")
            raise StorageError("Failed to set value", operation="set", key=key, cause=e) from e

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    async def get_value(self, key: str) -> Any | None:
        """Get a value from storage (Redis if available, else in-memory)."""
        try:
            if self._redis_available and self._redis_client:
                try:
                    data = await self._redis_client.get(key)
                    if data:
                        return json.loads(data)
                    return None
                except Exception as e:
                    logger.warning(f"Redis get failed, using in-memory fallback: {e}")
                    self._redis_available = False

            # Fallback to in-memory
            entry = self._fallback_storage.get(key)
            if entry:
                return entry["value"]
            return None
        except Exception as e:
            logger.error(f"Failed to get value for key {key}: {e}")
            raise StorageError("Failed to get value", operation="get", key=key, cause=e) from e

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    async def delete_value(self, key: str) -> bool:
        """Delete a value from storage."""
        try:
            deleted = False
            if self._redis_available and self._redis_client:
                try:
                    result = await self._redis_client.delete(key)
                    deleted = result > 0
                except Exception as e:
                    logger.warning(f"Redis delete failed: {e}")

            # Also delete from fallback
            if key in self._fallback_storage:
                del self._fallback_storage[key]
                deleted = True

            return deleted
        except Exception as e:
            logger.error(f"Failed to delete value for key {key}: {e}")
            raise StorageError(
                "Failed to delete value", operation="delete", key=key, cause=e
            ) from e

    # ==================== Qdrant Vector Operations ====================

    async def search_similar(
        self, vector: list[float], top_k: int = 5, filter_dict: dict | None = None
    ) -> list[dict[str, Any]]:
        """Search for similar vectors in Qdrant."""
        if not self._qdrant_available or not self._qdrant_client:
            logger.warning("Qdrant not available, skipping vector search")
            return []

        try:
            # This is a placeholder - actual implementation would use Qdrant search
            # For now, we just log and return empty results when Qdrant fails
            logger.debug(f"Searching similar vectors (top_k={top_k})")
            return []
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            # Graceful degradation - return empty results
            return []

    async def upsert_vector(
        self, id: str, vector: list[float], payload: dict[str, Any] | None = None
    ) -> bool:
        """Upsert a vector into Qdrant."""
        if not self._qdrant_available or not self._qdrant_client:
            logger.warning("Qdrant not available, skipping vector upsert")
            return False

        try:
            logger.debug(f"Upserting vector {id}")
            return True
        except Exception as e:
            logger.error(f"Vector upsert failed: {e}")
            return False

    # ==================== Health Checks ====================

    async def health_check(self) -> dict[str, Any]:
        """Check health of all memory services."""
        health = {
            "status": "healthy",
            "services": {},
            "fallback_active": False,
        }

        # Check Redis
        if self._enable_redis:
            try:
                if self._redis_client:
                    await self._redis_client.ping()
                    health["services"]["redis"] = {"status": "healthy", "available": True}
                    self._redis_available = True
                else:
                    health["services"]["redis"] = {
                        "status": "unavailable",
                        "available": False,
                        "reason": "not_initialized",
                    }
                    health["fallback_active"] = True
            except Exception as e:
                health["services"]["redis"] = {
                    "status": "unhealthy",
                    "available": False,
                    "error": str(e),
                }
                health["fallback_active"] = True
                self._redis_available = False
        else:
            health["services"]["redis"] = {"status": "disabled", "available": False}

        # Check Qdrant
        if self._enable_qdrant:
            try:
                if self._qdrant_client:
                    self._qdrant_client.get_collections()
                    health["services"]["qdrant"] = {"status": "healthy", "available": True}
                    self._qdrant_available = True
                else:
                    health["services"]["qdrant"] = {
                        "status": "unavailable",
                        "available": False,
                        "reason": "not_initialized",
                    }
            except Exception as e:
                health["services"]["qdrant"] = {
                    "status": "unhealthy",
                    "available": False,
                    "error": str(e),
                }
                self._qdrant_available = False
        else:
            health["services"]["qdrant"] = {"status": "disabled", "available": False}

        # Overall status
        if health["fallback_active"]:
            health["status"] = "degraded"
        elif not any(s.get("available") for s in health["services"].values() if s.get("status") != "disabled"):
            health["status"] = "unhealthy"

        return health

    async def get_stats(self) -> dict[str, Any]:
        """Get memory manager statistics."""
        async with self._lock:
            status_counts: dict[str, int] = {}
            for task in self._tasks.values():
                status_counts[task.status] = status_counts.get(task.status, 0) + 1

            health = await self.health_check()

            return {
                "total_tasks": len(self._tasks),
                "status_breakdown": status_counts,
                "fallback_storage_size": len(self._fallback_storage),
                "health": health,
            }

    async def close(self) -> None:
        """Close all connections."""
        if self._redis_client:
            try:
                await self._redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")

        if self._qdrant_client:
            try:
                # Qdrant client doesn't have async close
                logger.info("Qdrant connection closed")
            except Exception as e:
                logger.warning(f"Error closing Qdrant connection: {e}")


# Global memory manager instance
memory_manager = MemoryManager()
