"""WebSocket handler for Orkit Crew Gateway."""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core.memory import memory_manager

# WebSocket Router
websocket_router = APIRouter(tags=["websocket"])

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept and store a new connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total: {len(self.active_connections)}")

    async def disconnect(self, client_id: str) -> None:
        """Remove a connection."""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
        logger.info(f"Client {client_id} disconnected. Total: {len(self.active_connections)}")

    async def send_message(self, client_id: str, message: dict[str, Any]) -> bool:
        """Send a message to a specific client."""
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {e}")
                return False
        return False

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        disconnected = []
        for client_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)


# Global connection manager
manager = ConnectionManager()


@websocket_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    import uuid

    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "Connected to Orkit Crew Gateway",
        })

        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type", "unknown")

                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message_type == "subscribe_task":
                    task_id = message.get("task_id")
                    if task_id:
                        # Start task subscription
                        asyncio.create_task(
                            handle_task_subscription(client_id, websocket, task_id)
                        )
                        await websocket.send_json({
                            "type": "subscribed",
                            "task_id": task_id,
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "task_id is required for subscribe_task",
                        })

                elif message_type == "get_stats":
                    stats = await memory_manager.get_stats()
                    await websocket.send_json({
                        "type": "stats",
                        "data": stats,
                    })

                elif message_type == "list_crews":
                    from ..core.router import router as council_router

                    crews = council_router.get_available_crews()
                    await websocket.send_json({
                        "type": "crews",
                        "data": crews,
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })

    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await manager.disconnect(client_id)


async def handle_task_subscription(
    client_id: str, websocket: WebSocket, task_id: str
) -> None:
    """Handle subscription to a specific task's updates."""
    queue = await memory_manager.subscribe(task_id)

    if not queue:
        await websocket.send_json({
            "type": "error",
            "message": f"Task {task_id} not found",
        })
        return

    try:
        while True:
            # Wait for task updates with timeout
            try:
                update = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json({
                    "type": "task_update",
                    "task_id": task_id,
                    "data": update,
                })

                # Stop if task is complete
                if update.get("status") in ("completed", "failed", "cancelled"):
                    break

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Error in task subscription for {client_id}: {e}")
    finally:
        await memory_manager.unsubscribe(task_id, queue)
