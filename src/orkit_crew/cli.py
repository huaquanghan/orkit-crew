#!/usr/bin/env python3
"""CLI for Orkit Crew - PRD-to-Product Pipeline.

This CLI provides commands to run the PRD pipeline, resume sessions,
check status, and generate templates.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from orkit_crew.core.prd_parser import PRDParser
from orkit_crew.core.session import SessionManager
from orkit_crew.pipeline.orchestrator import PipelineOrchestrator


app = typer.Typer(
    name="orkit",
    help="Orkit Crew - PRD-to-Product Pipeline",
    rich_markup_mode="rich",
)
console = Console()


PRD_TEMPLATE = '''---
project_name: my-awesome-app
version: 1.0.0
mode: greenfield
scope: mvp
complexity: auto
stack:
  framework: nextjs
  language: typescript
  styling: tailwind
  ui_library: shadcn
  package_manager: pnpm
nextjs:
  router: app
  src_dir: true
output_dir: ./output
---

# 1. Overview

Brief description of your project.

# 2. Goals

- Primary goal
- Secondary goal

# 3. Features

## Feature 1: Core Feature
**Priority:** P0

### User Story
As a user, I want to...

### Description
Detailed description of the feature.

### Components
- [ ] Component A
- [ ] Component B

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Feature 2: Secondary Feature
**Priority:** P1

### User Story
As a user, I want to...

### Description
Description of secondary feature.

# 4. Page Structure

| Route | Page Name | Description | Auth Required |
|-------|-----------|-------------|---------------|
| / | Home | Landing page | No |
| /dashboard | Dashboard | Main dashboard | Yes |
| /login | Login | Authentication | No |

# 5. API Requirements

Describe API endpoints needed.

# 6. Database Schema

Describe data models.

# 7. Authentication

Describe auth requirements.

# 8. UI/UX Guidelines

Design system and styling guidelines.

# 9. Performance

Performance requirements.

# 10. Security

Security considerations.

# 11. Deployment

Deployment requirements.

# 12. Timeline

Project timeline and milestones.
'''


@app.command()
def prd(
    prd_file: str = typer.Argument(..., help="Path to PRD markdown file"),
    output: str = typer.Option(None, "--output", "-o", help="Output directory for generated files"),
    model: str = typer.Option("gpt-4", "--model", "-m", help="LLM model to use"),
    temperature: float = typer.Option(0.7, "--temperature", "-t", help="LLM temperature"),
) -> None:
    """Start PRD-to-Product pipeline from a PRD file."""
    prd_path = Path(prd_file)

    if not prd_path.exists():
        console.print(f"[red]Error: PRD file not found: {prd_file}[/red]")
        raise typer.Exit(1)

    console.print(Panel.fit(f"🚀 Orkit Crew Pipeline", style="blue"))
    console.print(f"PRD: [cyan]{prd_path.absolute()}[/cyan]")
    if output:
        console.print(f"Output: [cyan]{output}[/cyan]")

    # Validate PRD
    try:
        parser = PRDParser()
        doc = parser.parse_file(prd_path)

        if parser.warnings:
            console.print("[yellow]Warnings:[/yellow]")
            for warning in parser.warnings:
                console.print(f"  • {warning}")

        console.print(f"\n[green]✓ Valid PRD:[/green] [bold]{doc.metadata.project_name}[/bold]")

    except Exception as e:
        console.print(f"[red]Error parsing PRD: {e}[/red]")
        raise typer.Exit(1)

    # Run pipeline
    llm_config = {
        "model": model,
        "temperature": temperature,
    }

    orchestrator = PipelineOrchestrator(
        prd_path=str(prd_path),
        output_dir=output,
        llm_config=llm_config,
    )

    try:
        success = asyncio.run(orchestrator.run())
        if not success:
            raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted by user[/yellow]")
        raise typer.Exit(130)


@app.command()
def resume(
    directory: str = typer.Argument(".", help="Directory with existing session"),
    model: str = typer.Option("gpt-4", "--model", "-m", help="LLM model to use"),
    temperature: float = typer.Option(0.7, "--temperature", "-t", help="LLM temperature"),
) -> None:
    """Resume an existing pipeline session."""
    dir_path = Path(directory)

    if not dir_path.exists():
        console.print(f"[red]Error: Directory not found: {directory}[/red]")
        raise typer.Exit(1)

    session_manager = SessionManager(dir_path)

    if not session_manager.has_session():
        console.print(f"[red]Error: No session found in {directory}[/red]")
        console.print("Run [cyan]orkit prd <file>[/cyan] to start a new pipeline")
        raise typer.Exit(1)

    # Load session to get PRD path
    session = session_manager.load_session()

    llm_config = {
        "model": model,
        "temperature": temperature,
    }

    orchestrator = PipelineOrchestrator(
        prd_path=session.prd_file,
        output_dir=session.output_dir,
        llm_config=llm_config,
    )

    try:
        success = asyncio.run(orchestrator.resume())
        if not success:
            raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted by user[/yellow]")
        raise typer.Exit(130)


@app.command()
def status(
    directory: str = typer.Argument(".", help="Directory to check"),
) -> None:
    """Show current pipeline status."""
    dir_path = Path(directory)

    if not dir_path.exists():
        console.print(f"[red]Error: Directory not found: {directory}[/red]")
        raise typer.Exit(1)

    session_manager = SessionManager(dir_path)

    if not session_manager.has_session():
        console.print(f"[yellow]No active session in {directory}[/yellow]")
        console.print("Run [cyan]orkit prd <file>[/cyan] to start a pipeline")
        return

    # Load and display status
    session = session_manager.load_session()

    table = Table(title=f"Pipeline Status: {session.project_name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Session ID", session.session_id)
    table.add_row("Current Phase", session.current_phase.value)
    table.add_row("Analysis", session.analysis.status.value)
    table.add_row("Planning", session.planning.status.value)
    table.add_row("Generation", session.generation.status.value)
    table.add_row("Total Revisions", str(session.total_revisions))
    table.add_row("Generated Files", str(len(session.generated_files)))
    table.add_row("Created", session.created_at.strftime("%Y-%m-%d %H:%M"))
    table.add_row("Updated", session.updated_at.strftime("%Y-%m-%d %H:%M"))

    console.print(table)

    # Show recent files if any
    if session.generated_files:
        console.print("\n[bold]Recent Generated Files:[/bold]")
        for f in session.generated_files[-5:]:
            console.print(f"  • {f}")


@app.command()
def template(
    output: str = typer.Option("./prd.md", "--output", "-o", help="Output file path"),
) -> None:
    """Generate a blank PRD template file."""
    output_path = Path(output)

    if output_path.exists():
        if not typer.confirm(f"{output} already exists. Overwrite?"):
            console.print("Cancelled")
            raise typer.Exit(0)

    output_path.write_text(PRD_TEMPLATE, encoding="utf-8")
    console.print(f"[green]✓ Created PRD template:[/green] [cyan]{output_path.absolute()}[/cyan]")
    console.print("\n[dim]Edit the template with your project details, then run:[/dim]")
    console.print(f"  [cyan]orkit prd {output}[/cyan]")


@app.command()
def validate(
    prd_file: str = typer.Argument(..., help="Path to PRD file to validate"),
) -> None:
    """Validate a PRD file without running the pipeline."""
    prd_path = Path(prd_file)

    if not prd_path.exists():
        console.print(f"[red]Error: PRD file not found: {prd_file}[/red]")
        raise typer.Exit(1)

    console.print(Panel.fit(f"🔍 Validating PRD", style="blue"))

    try:
        parser = PRDParser()
        doc = parser.parse_file(prd_path)

        # Show metadata
        console.print("\n[bold]Metadata:[/bold]")
        console.print(f"  Project: {doc.metadata.project_name}")
        console.print(f"  Version: {doc.metadata.version}")
        console.print(f"  Mode: {doc.metadata.mode.value}")
        console.print(f"  Scope: {doc.metadata.scope.value}")
        console.print(f"  Complexity: {doc.metadata.complexity.value}")

        # Show stack
        console.print("\n[bold]Stack:[/bold]")
        console.print(f"  Framework: {doc.metadata.stack.framework}")
        console.print(f"  Language: {doc.metadata.stack.language}")
        console.print(f"  Styling: {doc.metadata.stack.styling}")
        console.print(f"  UI Library: {doc.metadata.stack.ui_library}")

        # Show features
        console.print(f"\n[bold]Features ({len(doc.content.features)}):[/bold]")
        for feature in doc.content.features[:10]:
            console.print(f"  • {feature.name} ({feature.priority.value})")
        if len(doc.content.features) > 10:
            console.print(f"  ... and {len(doc.content.features) - 10} more")

        # Show pages
        console.print(f"\n[bold]Pages ({len(doc.content.pages)}):[/bold]")
        for page in doc.content.pages[:10]:
            auth = " 🔒" if page.auth_required else ""
            console.print(f"  • {page.route} - {page.name}{auth}")
        if len(doc.content.pages) > 10:
            console.print(f"  ... and {len(doc.content.pages) - 10} more")

        # Show warnings
        if parser.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in parser.warnings:
                console.print(f"  ⚠ {warning}")
        else:
            console.print("\n[green]✓ No warnings[/green]")

        console.print("\n[green]✓ PRD is valid![/green]")

    except Exception as e:
        console.print(f"\n[red]✗ Validation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
    log_level: str = typer.Option("info", "--log-level", help="Logging level"),
) -> None:
    """Start the Gateway server (legacy mode)."""
    import subprocess

    gateway_cli = Path(__file__).parent.parent / "gateway" / "cli.py"

    cmd = [
        sys.executable,
        str(gateway_cli),
        "--host", host,
        "--port", str(port),
        "--log-level", log_level,
    ]

    if reload:
        cmd.append("--reload")

    console.print(Panel.fit("🌐 Starting Gateway Server", style="blue"))
    console.print(f"Host: [cyan]{host}[/cyan]")
    console.print(f"Port: [cyan]{port}[/cyan]")

    try:
        subprocess.call(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Gateway server stopped[/yellow]")


def main() -> Any:
    """Main entry point."""
    return app()


if __name__ == "__main__":
    main()
