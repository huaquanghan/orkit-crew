"""Planno LLM Gateway client."""

import json
from typing import Any

import httpx

from ..core.config import Config


class PlannoClient:
    """Client for interacting with Planno LLM Gateway."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.from_env()
        self.base_url = self.config.planno_api_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.config.planno_api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Send a chat completion request."""
        payload = {
            "model": model or self.config.default_model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def achat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Send an async chat completion request."""
        payload = {
            "model": model or self.config.default_model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def get_completion(self, prompt: str, model: str | None = None, **kwargs) -> str:
        """Get a simple text completion."""
        messages = [{"role": "user", "content": prompt}]
        response = self.chat(messages, model=model, **kwargs)
        return response["choices"][0]["message"]["content"]
