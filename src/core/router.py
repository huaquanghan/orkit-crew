"""Council Router for Orkit Crew."""

import asyncio
from collections.abc import Callable
from typing import Any

from .memory import MemoryManager, Task, memory_manager


class CouncilRouter:
    """Routes tasks to appropriate crews and manages execution."""

    # Available crew types
    CREW_TYPES = {
        "planning": "Planning Crew - Strategic planning and task breakdown",
        "coding": "Coding Crew - Code generation and implementation",
    }

    def __init__(self, memory: MemoryManager | None = None):
        self.memory = memory or memory_manager
        self._handlers: dict[str, Callable[[Task], asyncio.Task[Any]]] = {}
        self._running: set[asyncio.Task[Any]] = set()

    def register_handler(
        self, crew_type: str, handler: Callable[[Task], asyncio.Task[Any]]
    ) -> None:
        """Register a handler for a crew type."""
        self._handlers[crew_type] = handler

    async def submit_task(self, crew_type: str, description: str, metadata: dict[str, Any] | None = None) -> Task:
        """Submit a new task to be routed."""
        # Validate crew type
        if crew_type not in self.CREW_TYPES:
            raise ValueError(f"Unknown crew type: {crew_type}. Available: {list(self.CREW_TYPES.keys())}")

        # Create task
        task = await self.memory.create_task(crew_type, description, metadata)

        # Start processing
        asyncio.create_task(self._process_task(task))

        return task

    async def _process_task(self, task: Task) -> None:
        """Process a task through the appropriate crew."""
        try:
            # Update status to running
            await self.memory.update_task(task.id, status="running")

            # Get handler
            handler = self._handlers.get(task.crew_type)

            if handler:
                # Execute handler
                crew_task = handler(task)
                self._running.add(crew_task)
                try:
                    result = await crew_task
                    await self.memory.update_task(
                        task.id,
                        status="completed",
                        result=result if isinstance(result, dict) else {"output": str(result)},
                    )
                finally:
                    self._running.discard(crew_task)
            else:
                # No handler registered - simulate processing
                await asyncio.sleep(1)  # Simulate work
                await self.memory.update_task(
                    task.id,
                    status="completed",
                    result={"message": f"Task processed by {task.crew_type} crew (simulated)"},
                )

        except asyncio.CancelledError:
            await self.memory.update_task(task.id, status="cancelled")
            raise
        except Exception as e:
            await self.memory.update_task(
                task.id,
                status="failed",
                error=str(e),
            )

    async def cancel_task(self, task_id: str) -> Task | None:
        """Cancel a running task."""
        task = await self.memory.cancel_task(task_id)

        # Cancel any running asyncio tasks for this task
        for running_task in list(self._running):
            if running_task.get_name() == task_id:
                running_task.cancel()

        return task

    def get_available_crews(self) -> dict[str, str]:
        """Get list of available crews."""
        return self.CREW_TYPES.copy()

    async def get_task_status(self, task_id: str) -> Task | None:
        """Get the status of a task."""
        return await self.memory.get_task(task_id)


# Global router instance
router = CouncilRouter()
