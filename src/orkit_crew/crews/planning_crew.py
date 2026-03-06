"""Planning crew with Task Planner and Architect agents."""

from typing import List

from crewai import Agent, Task

from orkit_crew.crews.base import BaseCrew


class PlanningCrew(BaseCrew):
    """Crew for planning and architecture tasks."""
    
    def create_agents(self) -> List[Agent]:
        """Create planning agents."""
        config = self.get_agent_config("planning")
        
        task_planner = Agent(
            role="Task Planner",
            goal="Break down complex tasks into actionable steps",
            backstory="""You are an expert task planner with years of experience in 
            project management and system design. You excel at breaking down complex 
            requirements into clear, actionable steps. You think systematically and 
            always consider edge cases and dependencies.""",
            **config,
        )
        
        architect = Agent(
            role="System Architect",
            goal="Design robust and scalable system architectures",
            backstory="""You are a seasoned system architect who has designed systems 
            for Fortune 500 companies. You think about scalability, maintainability, 
            and best practices. You provide detailed technical recommendations and 
            architectural patterns.""",
            **config,
        )
        
        return [task_planner, architect]
    
    def create_tasks(self, agents: List[Agent], user_task: str) -> List[Task]:
        """Create planning tasks."""
        task_planner, architect = agents
        
        planning_task = Task(
            description=f"""Analyze the following task and create a detailed plan:
            
Task: {{task}}

Your output should include:
1. Task breakdown - list all subtasks
2. Dependencies between subtasks
3. Estimated complexity for each subtask
4. Recommended order of execution
5. Potential risks and mitigation strategies

Be thorough and think through all edge cases.""",
            expected_output="A comprehensive task plan with breakdown, dependencies, and recommendations",
            agent=task_planner,
        )
        
        architecture_task = Task(
            description=f"""Based on the task plan, design the system architecture:
            
Task: {{task}}

Your output should include:
1. High-level architecture diagram (described in text)
2. Component breakdown and responsibilities
3. Data flow between components
4. Technology stack recommendations
5. Scalability considerations
6. Security best practices to follow

Provide concrete, actionable recommendations.""",
            expected_output="A detailed system architecture document with component design and recommendations",
            agent=architect,
            context=[planning_task],
        )
        
        return [planning_task, architecture_task]
