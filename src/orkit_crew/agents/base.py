"""Base agent class for Orkit Crew agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from crewai import Agent

from orkit_crew.core.session import SessionManager


class BaseAgent(ABC):
    """Base class for all pipeline agents.

    Provides common functionality for agent configuration,
    session management, and output handling.
    """

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        llm_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize base agent.

        Args:
            session_manager: Optional session manager for state tracking.
            llm_config: Optional LLM configuration.
        """
        self.session_manager = session_manager
        self.llm_config = llm_config or {}
        self._agent: Agent | None = None

    @property
    @abstractmethod
    def role(self) -> str:
        """Agent role description."""
        ...

    @property
    @abstractmethod
    def goal(self) -> str:
        """Agent goal description."""
        ...

    @property
    @abstractmethod
    def backstory(self) -> str:
        """Agent backstory for personality."""
        ...

    def get_agent(self) -> Agent:
        """Get or create CrewAI agent instance.

        Returns:
            Configured CrewAI Agent.
        """
        if self._agent is None:
            self._agent = Agent(
                role=self.role,
                goal=self.goal,
                backstory=self.backstory,
                verbose=True,
                **self.llm_config,
            )
        return self._agent

    def log_output(self, content: str, output_type: str) -> None:
        """Log agent output to session if available.

        Args:
            content: Output content to log.
            output_type: Type of output (e.g., 'analysis', 'plan').
        """
        if self.session_manager:
            self.session_manager.log_decision(
                f"Agent output: {output_type}",
                context=content[:200] + "..." if len(content) > 200 else content,
            )

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> str:
        """Execute agent's main task.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Agent output as string.
        """
        ...
