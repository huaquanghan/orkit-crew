"""Base crew class with CrewAI integration."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from crewai import Agent, Crew, Process, Task

from orkit_crew.core.config import get_settings
from orkit_crew.core.memory import MemoryManager
from orkit_crew.gateway.plano_client import PlannoClient


@dataclass
class CrewResult:
    """Result from a crew execution."""
    output: str
    metadata: Dict[str, Any]
    execution_time: float
    token_usage: Optional[int] = None


class BaseCrew(ABC):
    """Base class for all crews."""
    
    def __init__(
        self,
        model: str = "planno",
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.model = model
        self.settings = get_settings()
        self.memory = memory_manager or MemoryManager()
        self.llm_client = PlannoClient()
        self._crew: Optional[Crew] = None
    
    @abstractmethod
    def create_agents(self) -> List[Agent]:
        """Create agents for this crew."""
        pass
    
    @abstractmethod
    def create_tasks(self, agents: List[Agent], user_task: str) -> List[Task]:
        """Create tasks for this crew."""
        pass
    
    def build_crew(self, user_task: str) -> Crew:
        """Build the crew with agents and tasks."""
        agents = self.create_agents()
        tasks = self.create_tasks(agents, user_task)
        
        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=self.settings.is_development,
            memory=self.settings.crewai_memory_enabled,
            cache=self.settings.crewai_cache_enabled,
        )
    
    async def execute(self, task: str, **kwargs) -> CrewResult:
        """Execute the crew with the given task."""
        import time
        
        start_time = time.time()
        
        try:
            crew = self.build_crew(task)
            result = crew.kickoff(inputs={"task": task, **kwargs})
            
            execution_time = time.time() - start_time
            
            return CrewResult(
                output=str(result),
                metadata={"task": task, "model": self.model},
                execution_time=execution_time,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return CrewResult(
                output=f"Error: {str(e)}",
                metadata={"error": str(e), "task": task},
                execution_time=execution_time,
            )
    
    def get_agent_config(self, role: str) -> Dict[str, Any]:
        """Get default agent configuration."""
        return {
            "llm": self.llm_client.get_crewai_llm(self.model),
            "verbose": self.settings.is_development,
            "allow_delegation": False,
        }
