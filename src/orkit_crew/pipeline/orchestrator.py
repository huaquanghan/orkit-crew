"""Pipeline Orchestrator - Main controller for PRD-to-Product pipeline.

This module provides the PipelineOrchestrator class that coordinates
all phases of the PRD pipeline with human review loops.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from orkit_crew.agents.analyst import PRDAnalystAgent
from orkit_crew.agents.architect import TaskArchitectAgent
from orkit_crew.agents.generator import CodeGeneratorAgent
from orkit_crew.core.config import get_settings
from orkit_crew.core.prd_parser import PRDDocument, parse_prd
from orkit_crew.core.session import PipelinePhase, SessionManager


console = Console()


class PipelineOrchestrator:
    """Main controller coordinating the PRD-to-Product pipeline.

    Coordinates:
    - PRD parsing
    - Session management
    - Agent execution (Phase 1, 2, 3)
    - Human review loops
    - State persistence
    """

    def __init__(
        self,
        prd_path: str,
        output_dir: str | None = None,
        llm_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize pipeline orchestrator.

        Args:
            prd_path: Path to PRD file.
            output_dir: Output directory for generated files.
            llm_config: Optional LLM configuration.
        """
        self.prd_path = Path(prd_path)
        self.output_dir = output_dir
        self.llm_config = llm_config or {}

        self.prd_doc: PRDDocument | None = None
        self.session_manager: SessionManager | None = None
        self.analysis: str = ""
        self.plan: str = ""
        self.generated_files: list[str] = []

        # Initialize agents
        self.analyst: PRDAnalystAgent | None = None
        self.architect: TaskArchitectAgent | None = None
        self.generator: CodeGeneratorAgent | None = None

    async def run(self) -> bool:
        """Run the full pipeline.

        Returns:
            True if pipeline completed successfully.
        """
        try:
            # Parse PRD
            console.print(Panel.fit("📄 Parsing PRD", style="blue"))
            self.prd_doc = parse_prd(self.prd_path)
            console.print(f"✓ Project: [bold]{self.prd_doc.metadata.project_name}[/bold]")
            console.print(f"✓ Features: {len(self.prd_doc.content.features)}")
            console.print(f"✓ Pages: {len(self.prd_doc.content.pages)}")

            # Initialize session
            output = self.output_dir or self.prd_doc.metadata.output_dir
            self.session_manager = SessionManager(output)

            if self.session_manager.has_session():
                if Confirm.ask("Existing session found. Resume?", default=True):
                    return await self.resume()

            self.session_manager.init_session(
                prd_file=str(self.prd_path),
                project_name=self.prd_doc.metadata.project_name,
                output_dir=output,
            )

            # Initialize agents with session
            self._init_agents()

            # Run phases
            if not await self.run_analysis():
                return False

            if not await self.run_planning():
                return False

            if not await self.run_generation():
                return False

            console.print(Panel.fit("✅ Pipeline Complete!", style="green"))
            return True

        except Exception as e:
            console.print(f"[red]Pipeline failed: {e}[/red]")
            if self.session_manager and self.session_manager.session:
                self.session_manager.fail_phase(
                    self.session_manager.session.current_phase,
                    str(e),
                )
            return False

    def _init_agents(self) -> None:
        """Initialize all agents with session manager."""
        settings = get_settings()

        llm_config = {
            "model": getattr(settings, "llm_model", "gpt-4"),
            "temperature": 0.7,
        }
        llm_config.update(self.llm_config)

        self.analyst = PRDAnalystAgent(
            session_manager=self.session_manager,
            llm_config=llm_config,
        )
        self.architect = TaskArchitectAgent(
            session_manager=self.session_manager,
            llm_config=llm_config,
        )
        self.generator = CodeGeneratorAgent(
            session_manager=self.session_manager,
            llm_config=llm_config,
        )

    async def run_analysis(self) -> bool:
        """Run Phase 1: Analysis with Q&A loop.

        Returns:
            True if analysis approved.
        """
        console.print(Panel.fit("🔍 Phase 1: Analysis", style="blue"))

        if not self.prd_doc or not self.analyst:
            raise RuntimeError("PRD not parsed or analyst not initialized")

        # Check if analysis already exists
        if self.session_manager:
            existing = self.session_manager.get_analysis()
            if existing:
                self.analysis = existing
                console.print("[yellow]Using existing analysis[/yellow]")
            else:
                # Generate analysis
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    progress.add_task("Analyzing PRD...", total=None)
                    self.analysis = await self.analyst.analyze(self.prd_doc)

        # Review loop
        approved = await self.review_loop("analysis", self.analysis)
        return approved

    async def run_planning(self) -> bool:
        """Run Phase 2: Planning with task review.

        Returns:
            True if plan approved.
        """
        console.print(Panel.fit("📋 Phase 2: Planning", style="blue"))

        if not self.prd_doc or not self.architect:
            raise RuntimeError("PRD not parsed or architect not initialized")

        # Check if plan already exists
        if self.session_manager:
            existing = self.session_manager.get_plan()
            if existing:
                self.plan = existing
                console.print("[yellow]Using existing plan[/yellow]")
            else:
                # Generate plan
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    progress.add_task("Creating task plan...", total=None)
                    mvp_only = self.prd_doc.metadata.scope.value == "mvp"
                    self.plan = await self.architect.plan(
                        self.prd_doc,
                        self.analysis,
                        mvp_only=mvp_only,
                    )

        # Review loop
        approved = await self.review_loop("plan", self.plan)
        return approved

    async def run_generation(self) -> bool:
        """Run Phase 3: Code Generation with task-by-task generation.

        Returns:
            True if generation completed.
        """
        console.print(Panel.fit("💻 Phase 3: Code Generation", style="blue"))

        if not self.prd_doc or not self.generator:
            raise RuntimeError("PRD not parsed or generator not initialized")

        if not self.output_dir:
            raise RuntimeError("Output directory not set")

        # Generate code
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Generating code...", total=None)
            self.generated_files = await self.generator.generate(
                prd_doc=self.prd_doc,
                analysis=self.analysis,
                plan=self.plan,
                output_dir=self.output_dir,
            )

        # Show summary
        console.print(f"\n[green]Generated {len(self.generated_files)} files:[/green]")
        for f in self.generated_files[:10]:
            console.print(f"  • {f}")
        if len(self.generated_files) > 10:
            console.print(f"  ... and {len(self.generated_files) - 10} more")

        # Approve generation
        if self.session_manager:
            self.session_manager.approve_phase(PipelinePhase.GENERATING)

        return True

    async def review_loop(
        self,
        phase: str,
        content: str,
    ) -> tuple[bool, str]:
        """Run review loop for a phase.

        Args:
            phase: Phase name (analysis, plan).
            content: Content to review.

        Returns:
            Tuple of (approved, final_content).
        """
        while True:
            # Show content preview
            if phase == "analysis":
                console.print(Panel(content[:2000] + "...", title="Analysis"))
            elif phase == "plan":
                # Show tasks table
                if self.architect:
                    table = Table(title="Tasks")
                    table.add_column("#", style="cyan")
                    table.add_column("Title", style="green")
                    table.add_column("Type", style="yellow")
                    table.add_column("Complexity", style="magenta")

                    for task in self.architect.tasks[:10]:
                        table.add_row(
                            str(task.get("number", "-")),
                            task.get("title", "")[:40],
                            task.get("type", ""),
                            task.get("complexity", ""),
                        )
                    console.print(table)

            # Ask for action
            action = Prompt.ask(
                f"\nWhat would you like to do with this {phase}?",
                choices=["approve", "edit", "redo", "skip"],
                default="approve",
            )

            if action == "approve":
                if self.session_manager:
                    if phase == "analysis":
                        self.session_manager.approve_phase(PipelinePhase.ANALYZING)
                    elif phase == "plan":
                        self.session_manager.approve_phase(PipelinePhase.PLANNING)
                return True

            elif action == "edit":
                # Show full content with syntax highlighting
                console.print(Syntax(content, "markdown", theme="monokai"))
                feedback = Prompt.ask("Enter your feedback for revision")

                if phase == "analysis" and self.analyst:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        progress.add_task("Revising analysis...", total=None)
                        content = await self.analyst.revise_analysis(
                            original_analysis=content,
                            qa_pairs=[{"question": "User feedback", "answer": feedback}],
                            prd_doc=self.prd_doc,
                        )
                    self.analysis = content

                elif phase == "plan" and self.architect:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        progress.add_task("Revising plan...", total=None)
                        content = await self.architect.revise_plan(content, feedback)
                    self.plan = content

            elif action == "redo":
                # Regenerate from scratch
                if phase == "analysis" and self.analyst:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        progress.add_task("Regenerating analysis...", total=None)
                        content = await self.analyst.analyze(self.prd_doc)
                    self.analysis = content

                elif phase == "plan" and self.architect:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        progress.add_task("Regenerating plan...", total=None)
                        mvp_only = self.prd_doc.metadata.scope.value == "mvp"
                        content = await self.architect.plan(
                            self.prd_doc,
                            self.analysis,
                            mvp_only=mvp_only,
                        )
                    self.plan = content

            elif action == "skip":
                console.print("[yellow]Skipping review...[/yellow]")
                return True

    async def resume(self) -> bool:
        """Resume an existing pipeline session.

        Returns:
            True if pipeline completed successfully.
        """
        if not self.session_manager:
            raise RuntimeError("Session manager not initialized")

        session = self.session_manager.load_session()
        console.print(Panel.fit(f"🔄 Resuming Session: {session.session_id}", style="blue"))
        console.print(f"Current phase: [bold]{session.current_phase.value}[/bold]")

        # Load existing content
        self.analysis = self.session_manager.get_analysis()
        self.plan = self.session_manager.get_plan()

        # Initialize agents
        self._init_agents()

        # Determine where to resume
        current = session.current_phase

        if current in [PipelinePhase.INIT, PipelinePhase.ANALYZING, PipelinePhase.ANALYSIS_REVIEW]:
            if not await self.run_analysis():
                return False
            if not await self.run_planning():
                return False
            if not await self.run_generation():
                return False

        elif current in [PipelinePhase.PLANNING, PipelinePhase.PLAN_REVIEW]:
            if not await self.run_planning():
                return False
            if not await self.run_generation():
                return False

        elif current in [PipelinePhase.GENERATING, PipelinePhase.GENERATION_REVIEW]:
            if not await self.run_generation():
                return False

        console.print(Panel.fit("✅ Pipeline Complete!", style="green"))
        return True

    def get_status(self) -> dict[str, Any]:
        """Get current pipeline status.

        Returns:
            Status dictionary.
        """
        if not self.session_manager or not self.session_manager.session:
            return {"status": "no_session"}

        session = self.session_manager.session
        return {
            "session_id": session.session_id,
            "project_name": session.project_name,
            "current_phase": session.current_phase.value,
            "analysis_status": session.analysis.status.value,
            "planning_status": session.planning.status.value,
            "generation_status": session.generation.status.value,
            "total_revisions": session.total_revisions,
            "generated_files": len(session.generated_files),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }
