"""Memory Manager for Orkit Crew."""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


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


class MemoryManager:
    """In-memory task storage with async support."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}

    async def create_task(self, crew_type: str, description: str, metadata: dict[str, Any] | None = None) -> Task:
        """Create a new task."""
        async with self._lock:
            task = Task(
                crew_type=crew_type,
                description=description,
                metadata=metadata or {},
            )
            self._tasks[task.id] = task
            self._subscribers[task.id] = []
            return task

    async def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_task(self, task_id: str, **kwargs) -> Task | None:
        """Update a task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)

            task.updated_at = time.time()

            # Notify subscribers
            await self._notify_subscribers(task)

            return task

    async def cancel_task(self, task_id: str) -> Task | None:
        """Cancel a task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            if task.status in ("completed", "failed", "cancelled"):
                return task

            task.update_status("cancelled")
            await self._notify_subscribers(task)
            return task

    async def list_tasks(self, status: str | None = None) -> list[Task]:
        """List all tasks, optionally filtered by status."""
        async with self._lock:
            tasks = list(self._tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            return tasks

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                del self._subscribers[task_id]
                return True
            return False

    async def subscribe(self, task_id: str) -> asyncio.Queue[dict[str, Any]] | None:
        """Subscribe to task updates."""
        async with self._lock:
            if task_id not in self._tasks:
                return None
            queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
            self._subscribers[task_id].append(queue)
            return queue

    async def unsubscribe(self, task_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Unsubscribe from task updates."""
        async with self._lock:
            if task_id in self._subscribers and queue in self._subscribers[task_id]:
                self._subscribers[task_id].remove(queue)

    async def _notify_subscribers(self, task: Task) -> None:
        """Notify all subscribers of a task update."""
        if task.id in self._subscribers:
            data = task.to_dict()
            for queue in self._subscribers[task.id]:
                try:
                    queue.put_nowait(data)
                except asyncio.QueueFull:
                    pass

    async def get_stats(self) -> dict[str, Any]:
        """Get memory manager statistics."""
        async with self._lock:
            status_counts: dict[str, int] = {}
            for task in self._tasks.values():
                status_counts[task.status] = status_counts.get(task.status, 0) + 1

            return {
                "total_tasks": len(self._tasks),
                "status_breakdown": status_counts,
            }


# Global memory manager instance
memory_manager = MemoryManager()
