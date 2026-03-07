"""LLM Client with async support, streaming, and retry logic.

This module provides a robust LLM client with:
- Async HTTP requests
- Streaming support
- Retry with exponential backoff
- Health checking
- Proper error handling
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from orkit_crew.core.config import get_settings


logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM.

    Attributes:
        content: The generated content.
        model: The model used for generation.
        usage: Token usage information.
        finish_reason: Reason for completion.
    """

    content: str
    model: str
    usage: dict[str, int] | None = None
    finish_reason: str | None = None


class LLMError(Exception):
    """Base exception for LLM client errors."""

    pass


class LLMConnectionError(LLMError):
    """Connection error to LLM service."""

    pass


class LLMRateLimitError(LLMError):
    """Rate limit exceeded error."""

    pass


class LLMAuthError(LLMError):
    """Authentication error."""

    pass


class LLMClient:
    """Async HTTP client for LLM Gateway with retry logic.

    Features:
    - Configurable timeout and retries
    - Exponential backoff for retries
    - Streaming support
    - Health checking
    - Detailed logging

    Example:
        ```python
        client = LLMClient()
        response = await client.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )
        print(response.content)
        ```
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize LLM client.

        Args:
            base_url: Base URL for LLM API. Defaults to settings.llm_base_url.
            api_key: API key for authentication. Defaults to settings.llm_api_key.
            model: Default model to use. Defaults to settings.llm_model.
            timeout: Request timeout in seconds. Defaults to 120.0.
            max_retries: Maximum number of retries. Defaults to 3.
        """
        settings = get_settings()

        self.base_url = (base_url or settings.llm_base_url or "http://localhost:8787").rstrip("/")
        self.api_key = api_key or settings.llm_api_key
        self.default_model = model or settings.llm_model or "gpt-4"
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

        logger.debug(f"LLMClient initialized with base_url: {self.base_url}")

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client.

        Returns:
            Configured async HTTP client.
        """
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
            logger.debug("Created new HTTP client")

        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug("Closed HTTP client")

    async def __aenter__(self) -> LLMClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        reraise=True,
    )
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Send a chat completion request.

        Args:
            messages: List of message dictionaries with role and content.
            model: Model to use. Defaults to default_model.
            temperature: Sampling temperature. Defaults to 0.7.
            max_tokens: Maximum tokens to generate. Defaults to None.

        Returns:
            LLMResponse with generated content.

        Raises:
            LLMConnectionError: If connection fails after retries.
            LLMRateLimitError: If rate limit is exceeded.
            LLMAuthError: If authentication fails.
            LLMError: For other errors.
        """
        use_model = model or self.default_model
        client = self._get_client()

        payload: dict[str, Any] = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        logger.debug(f"Sending chat request to {self.base_url}/v1/chat/completions")
        logger.debug(f"Model: {use_model}, Messages: {len(messages)}")

        try:
            response = await client.post("/v1/chat/completions", json=payload)

            # Handle specific error codes
            if response.status_code == 401:
                logger.error("Authentication failed - check API key")
                raise LLMAuthError("Invalid API key or authentication failed")

            if response.status_code == 429:
                logger.warning("Rate limit exceeded")
                raise LLMRateLimitError("Rate limit exceeded - please wait and retry")

            if response.status_code >= 500:
                logger.error(f"Server error: {response.status_code}")
                response.raise_for_status()

            response.raise_for_status()

            data = response.json()

            llm_response = LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=data.get("model", use_model),
                usage=data.get("usage"),
                finish_reason=data["choices"][0].get("finish_reason"),
            )

            logger.debug(f"Received response: {len(llm_response.content)} chars")
            return llm_response

        except httpx.ConnectError as e:
            logger.error(f"Connection error: {e}")
            raise LLMConnectionError(f"Failed to connect to LLM service at {self.base_url}") from e

        except httpx.TimeoutException as e:
            logger.error(f"Timeout error: {e}")
            raise LLMConnectionError(f"Request timed out after {self.timeout}s") from e

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            raise LLMError(f"HTTP error {e.response.status_code}: {e.response.text}") from e

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise LLMError(f"Unexpected error: {e}") from e

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream chat completion responses.

        Args:
            messages: List of message dictionaries.
            model: Model to use. Defaults to default_model.
            temperature: Sampling temperature. Defaults to 0.7.

        Yields:
            Content chunks as they are generated.

        Raises:
            LLMConnectionError: If connection fails.
            LLMError: For other errors.
        """
        use_model = model or self.default_model
        client = self._get_client()

        payload = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        logger.debug(f"Starting stream request with model: {use_model}")

        try:
            async with client.stream(
                "POST",
                "/v1/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"]
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.debug(f"Skipping malformed chunk: {e}")
                            continue

        except httpx.ConnectError as e:
            logger.error(f"Connection error during streaming: {e}")
            raise LLMConnectionError("Failed to connect to LLM service") from e

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise LLMError(f"Streaming error: {e}") from e

    async def health_check(self) -> bool:
        """Check if the LLM service is healthy.

        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            client = self._get_client()
            response = await client.get("/health", timeout=5.0)
            healthy = response.status_code == 200
            logger.debug(f"Health check: {'healthy' if healthy else 'unhealthy'}")
            return healthy
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def get_crewai_llm(self, model: str | None = None) -> dict[str, Any]:
        """Get LLM configuration for CrewAI.

        Args:
            model: Model to use. Defaults to default_model.

        Returns:
            Dictionary with LLM configuration for CrewAI.
        """
        return {
            "model": model or self.default_model,
            "base_url": f"{self.base_url}/v1",
            "api_key": self.api_key or "dummy-key",
        }


# Backward compatibility alias
PlannoClient = LLMClient
