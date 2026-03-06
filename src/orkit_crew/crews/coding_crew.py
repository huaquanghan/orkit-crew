"""Coding crew with Code Generator agent."""

from typing import List, Optional

from crewai import Agent, Task

from orkit_crew.crews.base import BaseCrew


class CodingCrew(BaseCrew):
    """Crew for code generation tasks."""
    
    def create_agents(self) -> List[Agent]:
        """Create coding agents."""
        config = self.get_agent_config("coding")
        
        code_generator = Agent(
            role="Code Generator",
            goal="Generate high-quality, production-ready code",
            backstory="""You are an elite software engineer with expertise in multiple 
            programming languages and frameworks. You write clean, well-documented, 
            and tested code. You follow best practices and industry standards. 
            You consider edge cases, error handling, and performance.""",
            **config,
        )
        
        return [code_generator]
    
    def create_tasks(self, agents: List[Agent], user_task: str) -> List[Task]:
        """Create coding tasks."""
        code_generator = agents[0]
        
        coding_task = Task(
            description=f"""Generate code for the following task:
            
Task: {{task}}
Context: {{context}}

Your output should include:
1. Complete, working code
2. Clear comments explaining key sections
3. Type hints where appropriate
4. Error handling
5. A brief explanation of how the code works

If the task is ambiguous, make reasonable assumptions and document them.
Ensure the code follows best practices and is production-ready.""",
            expected_output="Complete, documented code with explanation",
            agent=code_generator,
        )
        
        return [coding_task]
    
    async def execute(self, task: str, context: Optional[str] = None, **kwargs) -> str:
        """Execute coding task with optional context."""
        result = await super().execute(task, context=context or "", **kwargs)
        return result.output
