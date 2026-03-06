"""Chat Crew module for handling multi-turn conversations with LLM."""

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .base import BaseCrew, CrewContext, CrewResult, CrewStatus

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A single message in a chat conversation."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatMessage":
        """Create message from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ChatConfig:
    """Configuration for ChatCrew."""

    # LLM Configuration
    provider: str = "openai"  # "openai", "anthropic", "local"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    # System prompt
    system_prompt: str | None = None

    # Memory configuration
    enable_memory: bool = True
    max_history_messages: int = 50
    context_window: int = 10  # Number of recent messages to include

    # Function calling
    enable_functions: bool = False
    functions: list[dict[str, Any]] = field(default_factory=list)

    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0


class ChatCrew(BaseCrew):
    """Crew for handling chat conversations with LLM.

    Features:
    - Multi-turn conversations
    - Streaming responses
    - Memory integration (Redis + Qdrant)
    - Multiple LLM providers
    - Function calling support
    - Context management
    """

    def __init__(
        self,
        name: str = "chat_crew",
        context: CrewContext | None = None,
        config: ChatConfig | None = None,
        memory_manager: Any | None = None,
    ):
        super().__init__(name, context)
        self.config = config or ChatConfig()
        self._memory = memory_manager
        self._history: list[ChatMessage] = []
        self._session_id = self.context.session_id

    async def validate(self, **kwargs) -> tuple[bool, str | None]:
        """Validate chat inputs.

        Args:
            **kwargs: Must contain 'message' key with user input.

        Returns:
            tuple[bool, str | None]: (is_valid, error_message)
        """
        message = kwargs.get("message")
        if not message:
            return False, "Message is required"
        if not isinstance(message, str):
            return False, "Message must be a string"
        if len(message.strip()) == 0:
            return False, "Message cannot be empty"
        if len(message) > 100000:  # 100KB limit
            return False, "Message too long (max 100KB)"
        return True, None

    async def execute(self, **kwargs) -> CrewResult:
        """Execute a chat request (non-streaming).

        Args:
            **kwargs: Must contain 'message' key.

        Returns:
            CrewResult: The chat response.
        """
        is_valid, error = await self.validate(**kwargs)
        if not is_valid:
            self._set_status(CrewStatus.FAILED)
            self._set_error(error)
            return CrewResult(success=False, error=error)

        try:
            self._set_status(CrewStatus.RUNNING)
            message = kwargs["message"]

            # Add user message to history
            user_msg = ChatMessage(role="user", content=message)
            await self._add_message(user_msg)

            # Get LLM response
            response = await self._get_llm_response(stream=False)

            # Add assistant message to history
            assistant_msg = ChatMessage(role="assistant", content=response["content"])
            await self._add_message(assistant_msg)

            self._set_status(CrewStatus.COMPLETED)
            return CrewResult(
                success=True,
                data={
                    "message": assistant_msg.to_dict(),
                    "session_id": self._session_id,
                },
            )
        except Exception as e:
            logger.error(f"Chat execution failed: {e}")
            self._set_status(CrewStatus.FAILED)
            self._set_error(str(e))
            return CrewResult(success=False, error=str(e))

    async def chat(self, message: str, **kwargs) -> dict[str, Any]:
        """Send a chat message and get response.

        Args:
            message: User message.
            **kwargs: Additional options (temperature, max_tokens, etc.)

        Returns:
            dict[str, Any]: Response with message content and metadata.
        """
        result = await self.execute(message=message, **kwargs)
        if result.success:
            return result.data or {}
        raise Exception(result.error or "Unknown error")

    async def stream_chat(self, message: str, **kwargs) -> AsyncIterator[str]:
        """Send a chat message and get streaming response.

        Args:
            message: User message.
            **kwargs: Additional options.

        Yields:
            str: Chunks of the response.
        """
        is_valid, error = await self.validate(message=message)
        if not is_valid:
            raise ValueError(error)

        # Add user message to history
        user_msg = ChatMessage(role="user", content=message)
        await self._add_message(user_msg)

        # Stream LLM response
        full_response = ""
        async for chunk in self._get_llm_response_stream(**kwargs):
            full_response += chunk
            yield chunk

        # Add complete response to history
        assistant_msg = ChatMessage(role="assistant", content=full_response)
        await self._add_message(assistant_msg)

    async def get_history(
        self, limit: int | None = None, include_system: bool = False
    ) -> list[dict[str, Any]]:
        """Get conversation history.

        Args:
            limit: Maximum number of messages to return.
            include_system: Whether to include system messages.

        Returns:
            list[dict[str, Any]]: List of messages.
        """
        messages = self._history

        if not include_system:
            messages = [m for m in messages if m.role != "system"]

        if limit:
            messages = messages[-limit:]

        return [m.to_dict() for m in messages]

    async def clear_history(self) -> None:
        """Clear conversation history."""
        self._history = []

        # Clear from memory if available
        if self._memory and self.config.enable_memory:
            try:
                await self._memory.delete_value(f"chat:{self._session_id}:history")
            except Exception as e:
                logger.warning(f"Failed to clear history from memory: {e}")

    async def _add_message(self, message: ChatMessage) -> None:
        """Add a message to history and persist to memory."""
        self._history.append(message)

        # Trim history if needed
        if len(self._history) > self.config.max_history_messages:
            self._history = self._history[-self.config.max_history_messages :]

        # Persist to memory if available
        if self._memory and self.config.enable_memory:
            try:
                await self._memory.set_value(
                    f"chat:{self._session_id}:history",
                    [m.to_dict() for m in self._history],
                )

                # Store embedding for semantic search if Qdrant available
                if message.role in ("user", "assistant"):
                    await self._store_embedding(message)
            except Exception as e:
                logger.warning(f"Failed to persist message to memory: {e}")

    async def _store_embedding(self, message: ChatMessage) -> None:
        """Store message embedding in Qdrant for semantic search."""
        if not self._memory:
            return

        try:
            # Note: Actual embedding generation would require an embedding model
            # This is a placeholder for the integration point
            await self._memory.upsert_vector(
                id=f"{self._session_id}:{message.id}",
                vector=[],  # Would be actual embedding
                payload={
                    "session_id": self._session_id,
                    "message_id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                },
            )
        except Exception as e:
            logger.debug(f"Failed to store embedding: {e}")

    async def _get_relevant_context(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Retrieve relevant context from previous conversations."""
        if not self._memory:
            return []

        try:
            # Search for similar messages
            results = await self._memory.search_similar(
                vector=[],  # Would be query embedding
                top_k=top_k,
                filter_dict={"session_id": self._session_id},
            )
            return results
        except Exception as e:
            logger.debug(f"Failed to retrieve context: {e}")
            return []

    def _build_messages_for_llm(self, include_context: bool = True) -> list[dict[str, str]]:
        """Build message list for LLM API."""
        messages: list[dict[str, str]] = []

        # Add system prompt
        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})

        # Add relevant context from memory if enabled
        if include_context and self.config.enable_memory:
            # Get recent context window
            recent_messages = self._history[-self.config.context_window :]
            for msg in recent_messages:
                if msg.role in ("user", "assistant"):
                    messages.append({"role": msg.role, "content": msg.content})
        else:
            # Just add recent messages
            recent_messages = self._history[-self.config.context_window :]
            for msg in recent_messages:
                if msg.role in ("user", "assistant"):
                    messages.append({"role": msg.role, "content": msg.content})

        return messages

    async def _get_llm_response(
        self, stream: bool = False, **kwargs
    ) -> dict[str, Any]:
        """Get response from LLM."""
        messages = self._build_messages_for_llm()

        provider = kwargs.get("provider", self.config.provider)

        if provider == "openai":
            return await self._call_openai(messages, stream=False, **kwargs)
        elif provider == "anthropic":
            return await self._call_anthropic(messages, stream=False, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def _get_llm_response_stream(self, **kwargs) -> AsyncIterator[str]:
        """Get streaming response from LLM."""
        messages = self._build_messages_for_llm()
        provider = kwargs.get("provider", self.config.provider)

        if provider == "openai":
            async for chunk in self._call_openai_stream(messages, **kwargs):
                yield chunk
        elif provider == "anthropic":
            async for chunk in self._call_anthropic_stream(messages, **kwargs):
                yield chunk
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def _call_openai(
        self, messages: list[dict[str, str]], stream: bool = False, **kwargs
    ) -> dict[str, Any]:
        """Call OpenAI API."""
        import os

        import httpx

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": kwargs.get("model", self.config.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "frequency_penalty": kwargs.get(
                "frequency_penalty", self.config.frequency_penalty
            ),
            "presence_penalty": kwargs.get(
                "presence_penalty", self.config.presence_penalty
            ),
            "stream": stream,
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        async with httpx.AsyncClient() as client:
            for attempt in range(self.config.max_retries):
                try:
                    response = await client.post(
                        url, headers=headers, json=payload, timeout=60.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return {
                        "content": data["choices"][0]["message"]["content"],
                        "usage": data.get("usage", {}),
                        "model": data.get("model"),
                    }
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < self.config.max_retries - 1:
                        import asyncio

                        await asyncio.sleep(self.config.retry_delay * (2**attempt))
                        continue
                    raise
                except Exception as e:
                    if attempt < self.config.max_retries - 1:
                        import asyncio

                        await asyncio.sleep(self.config.retry_delay * (2**attempt))
                        continue
                    raise

        raise Exception("Max retries exceeded")

    async def _call_openai_stream(
        self, messages: list[dict[str, str]], **kwargs
    ) -> AsyncIterator[str]:
        """Call OpenAI API with streaming."""
        import os

        import httpx

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": kwargs.get("model", self.config.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }

        payload = {k: v for k, v in payload.items() if v is not None}

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST", url, headers=headers, json=payload, timeout=60.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue

    async def _call_anthropic(
        self, messages: list[dict[str, str]], stream: bool = False, **kwargs
    ) -> dict[str, Any]:
        """Call Anthropic API."""
        import os

        import httpx

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        # Separate system message
        system_message = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)

        payload: dict[str, Any] = {
            "model": kwargs.get("model", "claude-3-sonnet-20240229"),
            "messages": chat_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens or 1024),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": stream,
        }

        if system_message:
            payload["system"] = system_message

        async with httpx.AsyncClient() as client:
            for attempt in range(self.config.max_retries):
                try:
                    response = await client.post(
                        url, headers=headers, json=payload, timeout=60.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return {
                        "content": data["content"][0]["text"],
                        "usage": data.get("usage", {}),
                        "model": data.get("model"),
                    }
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < self.config.max_retries - 1:
                        import asyncio

                        await asyncio.sleep(self.config.retry_delay * (2**attempt))
                        continue
                    raise
                except Exception as e:
                    if attempt < self.config.max_retries - 1:
                        import asyncio

                        await asyncio.sleep(self.config.retry_delay * (2**attempt))
                        continue
                    raise

        raise Exception("Max retries exceeded")

    async def _call_anthropic_stream(
        self, messages: list[dict[str, str]], **kwargs
    ) -> AsyncIterator[str]:
        """Call Anthropic API with streaming."""
        import os

        import httpx

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        # Separate system message
        system_message = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)

        payload: dict[str, Any] = {
            "model": kwargs.get("model", "claude-3-sonnet-20240229"),
            "messages": chat_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens or 1024),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }

        if system_message:
            payload["system"] = system_message

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST", url, headers=headers, json=payload, timeout=60.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            chunk = json.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                if "text" in delta:
                                    yield delta["text"]
                        except json.JSONDecodeError:
                            continue

    async def load_history_from_memory(self) -> None:
        """Load conversation history from memory store."""
        if not self._memory or not self.config.enable_memory:
            return

        try:
            data = await self._memory.get_value(f"chat:{self._session_id}:history")
            if data:
                self._history = [ChatMessage.from_dict(m) for m in data]
        except Exception as e:
            logger.warning(f"Failed to load history from memory: {e}")
