"""PRD Analyst Agent - Phase 1 of the PRD-to-Product pipeline.

This agent analyzes PRD documents, extracts requirements, identifies ambiguities,
and conducts interactive Q&A with the user to clarify requirements.
"""

from __future__ import annotations

import re
from typing import Any

from crewai import Agent, Task
from crewai.tools import tool

from orkit_crew.agents.base import BaseAgent
from orkit_crew.core.prd_parser import PRDDocument
from orkit_crew.core.session import PipelinePhase, SessionManager


class PRDAnalystAgent(BaseAgent):
    """Agent for analyzing PRD documents.

    Reads a PRD, extracts key information, identifies ambiguities,
    and conducts interactive Q&A with the user.
    """

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        llm_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize PRD Analyst agent.

        Args:
            session_manager: Optional session manager for state tracking.
            llm_config: Optional LLM configuration for CrewAI.
        """
        super().__init__(session_manager, llm_config)
        self.questions: list[str] = []
        self.qa_pairs: list[dict[str, str]] = []

    @property
    def role(self) -> str:
        """Agent role."""
        return "PRD Analyst"

    @property
    def goal(self) -> str:
        """Agent goal."""
        return (
            "Analyze PRD documents thoroughly, extract all requirements, "
            "identify ambiguities and gaps, and produce a comprehensive "
            "analysis that serves as the foundation for project planning."
        )

    @property
    def backstory(self) -> str:
        """Agent backstory."""
        return (
            "You are a senior product analyst with 10+ years of experience "
            "translating business requirements into technical specifications. "
            "You have a keen eye for detail and can spot ambiguities, missing "
            "requirements, and potential risks. You excel at asking clarifying "
            "questions and documenting assumptions. Your analysis serves as "
            "the single source of truth for development teams."
        )

    async def analyze(
        self,
        prd_doc: PRDDocument,
        interactive: bool = True,
    ) -> str:
        """Analyze PRD and produce analysis document.

        Args:
            prd_doc: Parsed PRD document.
            interactive: Whether to conduct interactive Q&A.

        Returns:
            Analysis markdown content.
        """
        # Update session phase
        if self.session_manager:
            self.session_manager.start_phase(PipelinePhase.ANALYZING)

        # Generate initial analysis
        analysis = await self._generate_analysis(prd_doc)

        # Extract questions for interactive mode
        if interactive:
            self.questions = self.extract_questions(analysis)

        # Save to session
        if self.session_manager:
            self.session_manager.save_analysis(analysis)
            self.session_manager.complete_phase(PipelinePhase.ANALYZING)

        self.log_output(analysis, "analysis")
        return analysis

    async def _generate_analysis(self, prd_doc: PRDDocument) -> str:
        """Generate analysis from PRD document.

        Args:
            prd_doc: Parsed PRD document.

        Returns:
            Analysis markdown content.
        """
        # Build analysis prompt
        prompt = self._build_analysis_prompt(prd_doc)

        # Use CrewAI agent to generate analysis
        agent = self.get_agent()
        task = Task(
            description=prompt,
            agent=agent,
            expected_output="A comprehensive analysis document in markdown format",
        )

        # Execute task (synchronous for now)
        result = task.execute_sync()
        return str(result)

    def _build_analysis_prompt(self, prd_doc: PRDDocument) -> str:
        """Build prompt for analysis generation.

        Args:
            prd_doc: Parsed PRD document.

        Returns:
            Analysis prompt string.
        """
        # Extract PRD information
        metadata = prd_doc.metadata
        content = prd_doc.content

        # Build features section
        features_text = ""
        for feature in content.features:
            features_text += f"\n### {feature.name}\n"
            features_text += f"- Priority: {feature.priority.value}\n"
            features_text += f"- Description: {feature.description}\n"
            if feature.user_story:
                features_text += f"- User Story: {feature.user_story}\n"
            if feature.components:
                features_text += f"- Components: {', '.join(feature.components)}\n"
            if feature.criteria:
                features_text += f"- Acceptance Criteria: {', '.join(feature.criteria)}\n"

        # Build pages section
        pages_text = ""
        for page in content.pages:
            pages_text += f"\n- {page.route}: {page.name}"
            if page.auth_required:
                pages_text += " (requires auth)"

        prompt = f"""Analyze the following PRD and produce a comprehensive analysis document.

## PRD Information

**Project:** {metadata.project_name}
**Version:** {metadata.version}
**Mode:** {metadata.mode.value}
**Scope:** {metadata.scope.value}
**Complexity:** {metadata.complexity.value}

**Technology Stack:**
- Framework: {metadata.stack.framework}
- Language: {metadata.stack.language}
- Styling: {metadata.stack.styling}
- UI Library: {metadata.stack.ui_library}
- Package Manager: {metadata.stack.package_manager}

**Next.js Config:**
- Router: {metadata.nextjs.router}
- Src Directory: {metadata.nextjs.src_dir}

## Overview

{content.overview}

## Goals

{content.goals}

## Features

{features_text}

## Pages/Routes

{pages_text}

## Your Task

Produce a comprehensive analysis document with the following sections:

### 1. Summary
Brief overview of the project and its purpose.

### 2. Key Features Extracted
Create a table with columns: Feature, Priority, Complexity, Dependencies

### 3. Technical Requirements
List all technical requirements derived from the PRD.

### 4. Ambiguities & Questions
Identify any unclear requirements, missing information, or areas that need clarification.
For each ambiguity, formulate a specific question that would resolve it.
Format each question as: "QUESTION: [Your question here]"

### 5. Assumptions Made
Document any assumptions you're making due to missing information.

### 6. Complexity Assessment
Rate overall complexity (Low/Medium/High) with justification.

### 7. Risk Factors
Identify potential risks or challenges in implementation.

Be thorough and critical. If something is unclear or missing, call it out explicitly.
"""
        return prompt

    def extract_questions(self, analysis_text: str) -> list[str]:
        """Extract questions from analysis text.

        Args:
            analysis_text: Analysis markdown content.

        Returns:
            List of extracted questions.
        """
        questions = []

        # Look for QUESTION: pattern
        question_pattern = r"(?:QUESTION[:\s]+|Q[:\s]+)(.+?)(?=\n|$)"
        matches = re.finditer(question_pattern, analysis_text, re.IGNORECASE)
        for match in matches:
            question = match.group(1).strip()
            if question:
                questions.append(question)

        # Also look for numbered questions
        numbered_pattern = r"(?:^|\n)\d+\.\s*(.+?\?)"
        matches = re.finditer(numbered_pattern, analysis_text)
        for match in matches:
            question = match.group(1).strip()
            if question and question not in questions:
                questions.append(question)

        # Look for bullet questions
        bullet_pattern = r"(?:^|\n)[-\*]\s*(.+?\?)"
        matches = re.finditer(bullet_pattern, analysis_text)
        for match in matches:
            question = match.group(1).strip()
            if question and question not in questions:
                questions.append(question)

        return questions

    async def revise_analysis(
        self,
        original_analysis: str,
        qa_pairs: list[dict[str, str]],
        prd_doc: PRDDocument,
    ) -> str:
        """Revise analysis based on user Q&A.

        Args:
            original_analysis: Original analysis content.
            qa_pairs: List of question-answer pairs.
            prd_doc: Original PRD document.

        Returns:
            Revised analysis content.
        """
        # Build Q&A text
        qa_text = ""
        for i, pair in enumerate(qa_pairs, 1):
            qa_text += f"\n### Question {i}\n"
            qa_text += f"Q: {pair['question']}\n"
            qa_text += f"A: {pair['answer']}\n"

        prompt = f"""Revise the following analysis based on user answers to clarifying questions.

## Original Analysis

{original_analysis}

## User Q&A

{qa_text}

## Your Task

Produce a revised analysis that:
1. Incorporates the user's answers
2. Updates or removes resolved ambiguities
3. Maintains all sections from the original analysis
4. Updates the Summary if needed based on new information
5. Keeps the same markdown structure

The revised analysis should reflect the clarified requirements.
"""

        agent = self.get_agent()
        task = Task(
            description=prompt,
            agent=agent,
            expected_output="A revised analysis document in markdown format",
        )

        result = task.execute_sync()
        revised = str(result)

        # Save revised analysis
        if self.session_manager:
            self.session_manager.save_analysis(revised)

        return revised

    def get_complexity_assessment(self, analysis_text: str) -> dict[str, Any]:
        """Extract complexity assessment from analysis.

        Args:
            analysis_text: Analysis markdown content.

        Returns:
            Dictionary with complexity info.
        """
        result: dict[str, Any] = {
            "level": "medium",
            "justification": "",
            "factors": [],
        }

        # Look for complexity section
        complexity_pattern = r"(?:###?\s+6?\.?\s*Complexity Assessment.*?)\n+(.*?)(?=\n+###|\Z)"
        match = re.search(complexity_pattern, analysis_text, re.DOTALL | re.IGNORECASE)

        if match:
            section = match.group(1)

            # Extract level
            level_pattern = r"\b(low|medium|high)\b"
            level_match = re.search(level_pattern, section, re.IGNORECASE)
            if level_match:
                result["level"] = level_match.group(1).lower()

            # Extract justification (paragraph after level)
            lines = [l.strip() for l in section.split("\n") if l.strip()]
            if lines:
                result["justification"] = lines[0]

            # Extract factors (bullet points)
            factor_pattern = r"[-\*]\s*(.+)$"
            factors = re.findall(factor_pattern, section, re.MULTILINE)
            result["factors"] = factors

        return result

    async def execute(self, prd_doc: PRDDocument, **kwargs: Any) -> str:
        """Execute agent's main task.

        Args:
            prd_doc: Parsed PRD document.
            **kwargs: Additional arguments.

        Returns:
            Analysis content.
        """
        interactive = kwargs.get("interactive", True)
        return await self.analyze(prd_doc, interactive=interactive)
