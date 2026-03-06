"""Enhanced WebSocket handler for Orkit Crew Gateway with authentication and streaming."""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from ..core.exceptions import AuthenticationError, TaskNotFoundError, ValidationError
from ..core.memory import memory_manager
from ..core.router import router as council_router

# WebSocket Router
websocket_router = APIRouter(tags=["websocket"])

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types."""

    # Connection
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    # Heartbeat
    PING = "ping"
    PONG = "pong"
    HEARTBEAT = "heartbeat"

    # Task Management
    SUBSCRIBE_TASK = "subscribe_task"
    UNSUBSCRIBE_TASK = "unsubscribe_task"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    TASK_UPDATE = "task_update"

    # Chat/Streaming
    CHAT_MESSAGE = "chat_message"
    CHAT_STREAM = "chat_stream"
    CHAT_STREAM_START = "chat_stream_start"
    CHAT_STREAM_CHUNK = "chat_stream_chunk"
    CHAT_STREAM_END = "chat_stream_end"

    # System
    GET_STATS = "get_stats"
    STATS = "stats"
    LIST_CREWS = "list_crews"
    CREWS = "crews"
    AUTHENTICATE = "authenticate"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"


@dataclass
class ClientConnection:
    """Represents a WebSocket client connection."""

    client_id: str
    websocket: WebSocket
    authenticated: bool = False
    user_id: str | None = None
    subscriptions: set[str] = field(default_factory=set)
    connected_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    last_activity: float = field(default_factory=lambda: asyncio.get_event_loop().time())

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = asyncio.get_event_loop().time()


class ConnectionManager:
    """Manages WebSocket connections with authentication and subscription tracking."""

    def __init__(self):
        self.active_connections: dict[str, ClientConnection] = {}
        self._lock = asyncio.Lock()
        self._task_subscribers: dict[str, set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> ClientConnection:
        """Accept and store a new connection."""
        await websocket.accept()
        client = ClientConnection(client_id=client_id, websocket=websocket)
        async with self._lock:
            self.active_connections[client_id] = client
        logger.info(f"Client {client_id} connected. Total: {len(self.active_connections)}")
        return client

    async def disconnect(self, client_id: str) -> None:
        """Remove a connection and clean up subscriptions."""
        async with self._lock:
            client = self.active_connections.pop(client_id, None)
            if client:
                for task_id in list(client.subscriptions):
                    await self._unsubscribe_from_task(client_id, task_id)
        logger.info(f"Client {client_id} disconnected. Total: {len(self.active_connections)}")

    async def authenticate(self, client_id: str, token: str | None = None) -> bool:
        """Authenticate a client connection."""
        async with self._lock:
            client = self.active_connections.get(client_id)
            if not client:
                return False
            if token:
                client.authenticated = True
                client.user_id = f"user_{client_id[:8]}"
            else:
                client.authenticated = True
                client.user_id = f"anonymous_{client_id[:8]}"
            client.update_activity()
            return client.authenticated

    async def subscribe_to_task(self, client_id: str, task_id: str) -> bool:
        """Subscribe a client to task updates."""
        async with self._lock:
            client = self.active_connections.get(client_id)
            if not client:
                return False
            client.subscriptions.add(task_id)
            client.update_activity()
            if task_id not in self._task_subscribers:
                self._task_subscribers[task_id] = set()
            self._task_subscribers[task_id].add(client_id)
        logger.debug(f"Client {client_id} subscribed to task {task_id}")
        return True

    async def unsubscribe_from_task(self, client_id: str, task_id: str) -> bool:
        """Unsubscribe a client from task updates."""
        async with self._lock:
            return await self._unsubscribe_from_task(client_id, task_id)

    async def _unsubscribe_from_task(self, client_id: str, task_id: str) -> bool:
        """Internal unsubscribe (must be called with lock held)."""
        client = self.active_connections.get(client_id)
        if client:
            client.subscriptions.discard(task_id)
            client.update_activity()
        if task_id in self._task_subscribers:
            self._task_subscribers[task_id].discard(client_id)
            if not self._task_subscribers[task_id]:
                del self._task_subscribers[task_id]
        logger.debug(f"Client {client_id} unsubscribed from task {task_id}")
        return True

    async def send_message(self, client_id: str, message: dict[str, Any]) -> bool:
        """Send a message to a specific client."""
        client = self.active_connections.get(client_id)
        if not client:
            return False
        try:
            await client.websocket.send_json(message)
            client.update_activity()
            return True
        except Exception as e:
            logger.error(f"Error sending to {client_id}: {e}")
            await self.disconnect(client_id)
            return False

    async def broadcast(self, message: dict[str, Any], exclude: str | None = None) -> None:
        """Broadcast a message to all connected clients."""
        disconnected = []
        for client_id, client in list(self.active_connections.items()):
            if client_id == exclude:
                continue
            try:
                await client.websocket.send_json(message)
                client.update_activity()
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected.append(client_id)
        for client_id in disconnected:
            await self.disconnect(client_id)

    async def broadcast_task_update(self, task_id: str, update: dict[str, Any]) -> None:
        """Broadcast a task update to all subscribers."""
        async with self._lock:
            subscribers = self._task_subscribers.get(task_id, set()).copy()
        message = {
            "type": MessageType.TASK_UPDATE.value,
            "task_id": task_id,
            "data": update,
        }
        for client_id in subscribers:
            await self.send_message(client_id, message)

    async def broadcast_chat_stream(
        self, task_id: str, chunk: str, is_start: bool = False, is_end: bool = False
    ) -> None:
        """Broadcast a chat stream chunk to all subscribers."""
        async with self._lock:
            subscribers = self._task_subscribers.get(task_id, set()).copy()
        if is_start:
            message_type = MessageType.CHAT_STREAM_START.value
        elif is_end:
            message_type = MessageType.CHAT_STREAM_END.value
        else:
            message_type = MessageType.CHAT_STREAM_CHUNK.value
        message = {
            "type": message_type,
            "task_id": task_id,
            "data": {"chunk": chunk} if not (is_start or is_end) else {},
        }
        for client_id in subscribers:
            await self.send_message(client_id, message)

    def get_connection_info(self, client_id: str) -> dict[str, Any] | None:
        """Get connection info for a client."""
        client = self.active_connections.get(client_id)
        if not client:
            return None
        return {
            "client_id": client.client_id,
            "user_id": client.user_id,
            "authenticated": client.authenticated,
            "subscriptions": list(client.subscriptions),
            "connected_at": client.connected_at,
            "last_activity": client.last_activity,
        }


# Global connection manager
manager = ConnectionManager()


@websocket_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates with authentication."""
    import uuid

    client_id = str(uuid.uuid4())
    client = await manager.connect(websocket, client_id)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": MessageType.CONNECTED.value,
            "client_id": client_id,
            "message": "Connected to Orkit Crew Gateway",
            "authenticated": False,
        })

        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type", "unknown")

                if message_type == MessageType.PING.value:
                    await websocket.send_json({"type": MessageType.PONG.value})

                elif message_type == MessageType.AUTHENTICATE.value:
                    token = message.get("token")
                    success = await manager.authenticate(client_id, token)
                    if success:
                        await websocket.send_json({
                            "type": MessageType.AUTH_SUCCESS.value,
                            "client_id": client_id,
                            "user_id": client.user_id,
                        })
                    else:
                        await websocket.send_json({
                            "type": MessageType.AUTH_FAILED.value,
                            "message": "Authentication failed",
                        })

                elif message_type == MessageType.SUBSCRIBE_TASK.value:
                    task_id = message.get("task_id")
                    if not task_id:
                        await websocket.send_json({
                            "type": MessageType.ERROR.value,
                            "message": "task_id is required for subscribe_task",
                        })
                        continue

                    # Check if task exists
                    task = await memory_manager.get_task(task_id)
                    if not task:
                        await websocket.send_json({
                            "type": MessageType.ERROR.value,
                            "code": "task_not_found",
                            "message": f"Task {task_id} not found",
                        })
                        continue

                    await manager.subscribe_to_task(client_id, task_id)
                    await websocket.send_json({
                        "type": MessageType.SUBSCRIBED.value,
                        "task_id": task_id,
                    })

                    # Start task subscription handler
                    asyncio.create_task(handle_task_subscription(client_id, task_id))

                elif message_type == MessageType.UNSUBSCRIBE_TASK.value:
                    task_id = message.get("task_id")
                    if task_id:
                        await manager.unsubscribe_from_task(client_id, task_id)
                        await websocket.send_json({
                            "type": MessageType.UNSUBSCRIBED.value,
                            "task_id": task_id,
                        })
                    else:
                        await websocket.send_json({
                            "type": MessageType.ERROR.value,
                            "message": "task_id is required for unsubscribe_task",
                        })

                elif message_type == MessageType.GET_STATS.value:
                    stats = await memory_manager.get_stats()
                    await websocket.send_json({
                        "type": MessageType.STATS.value,
                        "data": stats,
                    })

                elif message_type == MessageType.LIST_CREWS.value:
                    crews = council_router.get_available_crews()
                    await websocket.send_json({
                        "type": MessageType.CREWS.value,
                        "data": crews,
                    })

                elif message_type == MessageType.CHAT_MESSAGE.value:
                    # Handle chat messages for real-time streaming
                    task_id = message.get("task_id")
                    content = message.get("content")
                    if task_id and content:
                        # Broadcast chat message to all subscribers
                        await manager.broadcast_chat_stream(
                            task_id, content, is_start=True
                        )
                        await manager.broadcast_chat_stream(task_id, content, is_end=True)
                    else:
                        await websocket.send_json({
                            "type": MessageType.ERROR.value,
                            "message": "task_id and content are required for chat_message",
                        })

                else:
                    await websocket.send_json({
                        "type": MessageType.ERROR.value,
                        "code": "unknown_message_type",
                        "message": f"Unknown message type: {message_type}",
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": MessageType.ERROR.value,
                    "code": "invalid_json",
                    "message": "Invalid JSON format",
                })

    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await manager.disconnect(client_id)


async def handle_task_subscription(client_id: str, task_id: str) -> None:
    """Handle subscription to a specific task's updates."""
    queue = await memory_manager.subscribe(task_id)

    if not queue:
        await manager.send_message(client_id, {
            "type": MessageType.ERROR.value,
            "code": "task_not_found",
            "message": f"Task {task_id} not found",
        })
        return

    try:
        while True:
            try:
                update = await asyncio.wait_for(queue.get(), timeout=30.0)
                await manager.send_message(client_id, {
                    "type": MessageType.TASK_UPDATE.value,
                    "task_id": task_id,
                    "data": update,
                })

                # Stop if task is complete
                if update.get("status") in ("completed", "failed", "cancelled"):
                    break

            except asyncio.TimeoutError:
                # Send heartbeat
                await manager.send_message(client_id, {
                    "type": MessageType.HEARTBEAT.value,
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Error in task subscription for {client_id}: {e}")
    finally:
        await memory_manager.unsubscribe(task_id, queue)
        await manager.unsubscribe_from_task(client_id, task_id)
