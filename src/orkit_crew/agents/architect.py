"""Task Architect Agent - Phase 2 of the PRD-to-Product pipeline.

This agent takes the PRD and approved analysis to produce a detailed
task breakdown plan with project structure and implementation steps.
"""

from __future__ import annotations

import re
from typing import Any

from crewai import Agent, Task

from orkit_crew.agents.base import BaseAgent
from orkit_crew.core.prd_parser import PRDDocument
from orkit_crew.core.session import PipelinePhase, SessionManager


class TaskArchitectAgent(BaseAgent):
    """Agent for creating detailed task plans from PRD and analysis.

    Breaks down analyzed PRD into detailed, ordered task plan with
    project structure, file paths, and dependencies.
    """

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        llm_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Task Architect agent.

        Args:
            session_manager: Optional session manager for state tracking.
            llm_config: Optional LLM configuration for CrewAI.
        """
        super().__init__(session_manager, llm_config)
        self.tasks: list[dict[str, Any]] = []

    @property
    def role(self) -> str:
        """Agent role."""
        return "Task Architect"

    @property
    def goal(self) -> str:
        """Agent goal."""
        return (
            "Transform PRD and analysis into a detailed, actionable task plan "
            "with clear file structure, implementation order, and dependencies. "
            "Ensure the plan follows Next.js App Router conventions and best practices."
        )

    @property
    def backstory(self) -> str:
        """Agent backstory."""
        return (
            "You are a senior frontend architect with 10+ years of experience, "
            "specializing in Next.js, React, TypeScript, and modern UI development. "
            "You excel at breaking down complex requirements into manageable tasks, "
            "designing clean project structures, and identifying dependencies. "
            "Your plans are known for being thorough, practical, and easy to follow. "
            "You always consider the developer experience and maintainability."
        )

    async def plan(
        self,
        prd_doc: PRDDocument,
        analysis_content: str,
        mvp_only: bool = True,
    ) -> str:
        """Create task plan from PRD and analysis.

        Args:
            prd_doc: Parsed PRD document.
            analysis_content: Approved analysis content.
            mvp_only: Whether to include only MVP features.

        Returns:
            Plan markdown content.
        """
        # Update session phase
        if self.session_manager:
            self.session_manager.start_phase(PipelinePhase.PLANNING)

        # Generate plan
        plan = await self._generate_plan(prd_doc, analysis_content, mvp_only)

        # Parse tasks for later use
        self.tasks = self.parse_tasks(plan)

        # Save to session
        if self.session_manager:
            self.session_manager.save_plan(plan)
            self.session_manager.complete_phase(PipelinePhase.PLANNING)

        self.log_output(plan, "plan")
        return plan

    async def _generate_plan(
        self,
        prd_doc: PRDDocument,
        analysis_content: str,
        mvp_only: bool,
    ) -> str:
        """Generate plan from PRD and analysis.

        Args:
            prd_doc: Parsed PRD document.
            analysis_content: Approved analysis content.
            mvp_only: Whether to include only MVP features.

        Returns:
            Plan markdown content.
        """
        prompt = self._build_plan_prompt(prd_doc, analysis_content, mvp_only)

        agent = self.get_agent()
        task = Task(
            description=prompt,
            agent=agent,
            expected_output="A detailed task plan in markdown format",
        )

        result = task.execute_sync()
        return str(result)

    def _build_plan_prompt(
        self,
        prd_doc: PRDDocument,
        analysis_content: str,
        mvp_only: bool,
    ) -> str:
        """Build prompt for plan generation.

        Args:
            prd_doc: Parsed PRD document.
            analysis_content: Approved analysis content.
            mvp_only: Whether to include only MVP features.

        Returns:
            Plan prompt string.
        """
        metadata = prd_doc.metadata
        content = prd_doc.content

        # Get features based on scope
        features = prd_doc.get_mvp_features() if mvp_only else content.features

        features_text = ""
        for feature in features:
            features_text += f"\n- {feature.name} ({feature.priority.value})"
            if feature.description:
                features_text += f": {feature.description}"

        pages_text = ""
        for page in content.pages:
            pages_text += f"\n- {page.route}: {page.name}"
            if page.auth_required:
                pages_text += " (auth required)"

        scope_note = "MVP features only" if mvp_only else "All features (full scope)"

        prompt = f"""Create a detailed implementation plan based on the following PRD and analysis.

## PRD Information

**Project:** {metadata.project_name}
**Scope:** {scope_note}

**Technology Stack:**
- Framework: {metadata.stack.framework}
- Language: {metadata.stack.language}
- Styling: {metadata.stack.styling}
- UI Library: {metadata.stack.ui_library}
- Package Manager: {metadata.stack.package_manager}
- Router: {metadata.nextjs.router}
- Src Directory: {metadata.nextjs.src_dir}

## Features to Implement

{features_text}

## Pages/Routes

{pages_text}

## Approved Analysis

{analysis_content}

## Your Task

Create a comprehensive implementation plan with the following sections:

### 1. Tech Stack
List all technologies, libraries, and versions to be used.

### 2. Project Structure
Show the complete directory tree following Next.js App Router conventions:
```
my-app/
├── src/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── types/
├── public/
└── ...
```

### 3. Tasks
Create numbered tasks in implementation order. For each task include:

**Task N: [Title]**
- **Type:** setup | config | component | page | api | integration | test
- **Files:** Specific file paths (e.g., `src/app/page.tsx`)
- **Description:** What needs to be implemented
- **Dependencies:** Task numbers this depends on
- **Complexity:** low | medium | high
- **Acceptance Criteria:** How to verify completion

Example:
**Task 1: Initialize Next.js Project**
- **Type:** setup
- **Files:** `package.json`, `next.config.js`, `tsconfig.json`
- **Description:** Create new Next.js project with TypeScript and Tailwind
- **Dependencies:** None
- **Complexity:** low
- **Acceptance Criteria:** Project runs with `npm run dev`

### 4. Dependency Graph
Show task dependencies in a visual format:
```
Task 1 → Task 2 → Task 4
     → Task 3 → Task 5
```

### 5. Summary
- Total tasks
- Estimated complexity breakdown
- Key milestones

Important:
- Use specific file paths, not generic descriptions
- Follow Next.js App Router conventions
- Consider shadcn/ui component patterns
- Include proper TypeScript types
- Order tasks by dependencies, not just sequentially
"""
        return prompt

    def parse_tasks(self, plan_content: str) -> list[dict[str, Any]]:
        """Extract tasks from plan content.

        Args:
            plan_content: Plan markdown content.

        Returns:
            List of task dictionaries.
        """
        tasks: list[dict[str, Any]] = []

        # Pattern to match task headers (with or without bold)
        task_pattern = r"\*\*Task\s+(\d+):\s*([^\*]+)\*\*"

        for match in re.finditer(task_pattern, plan_content):
            task_num = int(match.group(1))
            task_title = match.group(2).strip()

            # Find task section
            start_pos = match.end()
            next_task = re.search(r"\*\*Task\s+\d+:", plan_content[start_pos:])
            if next_task:
                end_pos = start_pos + next_task.start()
                task_section = plan_content[start_pos:end_pos]
            else:
                task_section = plan_content[start_pos:]

            task = self._parse_task_section(task_num, task_title, task_section)
            tasks.append(task)

        return tasks

    def _parse_task_section(
        self,
        task_num: int,
        task_title: str,
        task_section: str,
    ) -> dict[str, Any]:
        """Parse individual task section.

        Args:
            task_num: Task number.
            task_title: Task title.
            task_section: Task section content.

        Returns:
            Task dictionary.
        """
        task: dict[str, Any] = {
            "number": task_num,
            "title": task_title,
            "type": "",
            "files": [],
            "description": "",
            "dependencies": [],
            "complexity": "medium",
            "criteria": [],
        }

        # Extract type (with or without bold)
        type_match = re.search(r"[\*\-]\s*\*?Type:?\*?\*?:?\s*(\w+)", task_section)
        if type_match:
            task["type"] = type_match.group(1).lower()

        # Extract files (with or without bold)
        files_match = re.search(r"[\*\-]\s*\*?Files:?\*?\*?:?\s*(.+?)(?=\n|$)", task_section)
        if files_match:
            files_text = files_match.group(1)
            # Extract code-formatted file paths
            task["files"] = re.findall(r"`([^`]+)`", files_text)

        # Extract description (with or without bold)
        desc_match = re.search(r"[\*\-]\s*\*?Description:?\*?\*?:?\s*(.+?)(?=\n[\*\-]|\Z)", task_section, re.DOTALL)
        if desc_match:
            task["description"] = desc_match.group(1).strip()

        # Extract dependencies (with or without bold)
        deps_match = re.search(r"[\*\-]\s*\*?Dependencies:?\*?\*?:?\s*(.+?)(?=\n|$)", task_section)
        if deps_match:
            deps_text = deps_match.group(1)
            # Extract task numbers
            task["dependencies"] = [int(n) for n in re.findall(r"Task\s+(\d+)", deps_text)]

        # Extract complexity (with or without bold)
        complexity_match = re.search(r"[\*\-]\s*\*?Complexity:?\*?\*?:?\s*(\w+)", task_section)
        if complexity_match:
            task["complexity"] = complexity_match.group(1).lower()

        # Extract acceptance criteria (with or without bold)
        criteria_match = re.search(r"[\*\-]\s*\*?Acceptance Criteria:?\*?\*?:?\s*(.+?)(?=\n[\*\-]|\Z)", task_section, re.DOTALL)
        if criteria_match:
            criteria_text = criteria_match.group(1)
            # Split by semicolon or bullet
            task["criteria"] = [c.strip() for c in re.split(r"[;\n]", criteria_text) if c.strip()]

        return task

    async def revise_task(
        self,
        task_dict: dict[str, Any],
        feedback: str,
        full_plan: str,
    ) -> str:
        """Revise a single task based on feedback.

        Args:
            task_dict: Task dictionary to revise.
            feedback: User feedback.
            full_plan: Full plan content for context.

        Returns:
            Revised task content.
        """
        prompt = f"""Revise the following task based on user feedback.

## Full Plan Context

{full_plan[:1000]}...

## Task to Revise

**Task {task_dict['number']}: {task_dict['title']}**
- **Type:** {task_dict['type']}
- **Files:** {', '.join(task_dict['files'])}
- **Description:** {task_dict['description']}
- **Dependencies:** {task_dict['dependencies']}
- **Complexity:** {task_dict['complexity']}
- **Acceptance Criteria:** {', '.join(task_dict['criteria'])}

## User Feedback

{feedback}

## Your Task

Provide the revised task in the same format:
**Task {task_dict['number']}: [Title]**
- **Type:** ...
- **Files:** ...
- **Description:** ...
- **Dependencies:** ...
- **Complexity:** ...
- **Acceptance Criteria:** ...
"""

        agent = self.get_agent()
        task = Task(
            description=prompt,
            agent=agent,
            expected_output="A revised task in the same format",
        )

        result = task.execute_sync()
        return str(result)

    async def revise_plan(
        self,
        plan_content: str,
        feedback: str,
    ) -> str:
        """Revise entire plan based on feedback.

        Args:
            plan_content: Current plan content.
            feedback: User feedback.

        Returns:
            Revised plan content.
        """
        prompt = f"""Revise the following implementation plan based on user feedback.

## Current Plan

{plan_content}

## User Feedback

{feedback}

## Your Task

Produce a revised plan that addresses the feedback while maintaining:
1. Same overall structure (Tech Stack, Project Structure, Tasks, etc.)
2. Next.js App Router conventions
3. Proper task ordering and dependencies
4. Specific file paths

The revised plan should incorporate all feedback points.
"""

        agent = self.get_agent()
        task = Task(
            description=prompt,
            agent=agent,
            expected_output="A revised implementation plan in markdown format",
        )

        result = task.execute_sync()
        revised = str(result)

        # Update parsed tasks
        self.tasks = self.parse_tasks(revised)

        # Save to session
        if self.session_manager:
            self.session_manager.save_plan(revised)

        return revised

    def get_task_by_number(self, task_number: int) -> dict[str, Any] | None:
        """Get task by number.

        Args:
            task_number: Task number.

        Returns:
            Task dictionary or None.
        """
        for task in self.tasks:
            if task["number"] == task_number:
                return task
        return None

    def get_tasks_by_type(self, task_type: str) -> list[dict[str, Any]]:
        """Get tasks by type.

        Args:
            task_type: Task type (setup, config, component, etc.).

        Returns:
            List of task dictionaries.
        """
        return [t for t in self.tasks if t["type"] == task_type]

    def get_tasks_by_complexity(self, complexity: str) -> list[dict[str, Any]]:
        """Get tasks by complexity.

        Args:
            complexity: Complexity level (low, medium, high).

        Returns:
            List of task dictionaries.
        """
        return [t for t in self.tasks if t["complexity"] == complexity]

    async def execute(
        self,
        prd_doc: PRDDocument,
        analysis_content: str,
        **kwargs: Any,
    ) -> str:
        """Execute agent's main task.

        Args:
            prd_doc: Parsed PRD document.
            analysis_content: Approved analysis content.
            **kwargs: Additional arguments.

        Returns:
            Plan content.
        """
        mvp_only = kwargs.get("mvp_only", True)
        return await self.plan(prd_doc, analysis_content, mvp_only=mvp_only)
