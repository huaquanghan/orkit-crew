"""CLI for Orkit Crew."""

import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from orkit_crew.core.config import get_settings
from orkit_crew.core.router import CouncilRouter
from orkit_crew.crews.planning_crew import PlanningCrew
from orkit_crew.crews.coding_crew import CodingCrew

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="orkit")
def cli() -> None:
    """Orkit Crew - AI Crew Orchestration System."""
    pass


@cli.command()
@click.argument("task")
@click.option("--model", "-m", default="planno", help="Model to use for planning")
def plan(task: str, model: str) -> None:
    """Run planning crew for a task."""
    console.print(Panel(f"[bold blue]Planning Task:[/] {task}", title="Orkit"))
    
    async def run_planning() -> None:
        crew = PlanningCrew(model=model)
        result = await crew.execute(task)
        console.print("\n[bold green]Planning Result:[/]")
        console.print(result)
    
    asyncio.run(run_planning())


@cli.command()
@click.argument("task")
@click.option("--model", "-m", default="planno", help="Model to use for coding")
@click.option("--context", "-c", help="Additional context for code generation")
def code(task: str, model: str, context: Optional[str]) -> None:
    """Run coding crew to generate code."""
    console.print(Panel(f"[bold green]Coding Task:[/] {task}", title="Orkit"))
    
    async def run_coding() -> None:
        crew = CodingCrew(model=model)
        result = await crew.execute(task, context=context)
        console.print("\n[bold cyan]Generated Code:[/]")
        console.print(result)
    
    asyncio.run(run_coding())


@cli.command()
@click.option("--model", "-m", default="planno", help="Default model for chat")
def chat(model: str) -> None:
    """Interactive chat mode with router."""
    console.print(Panel(
        "[bold yellow]Welcome to Orkit Chat![/]\n"
        "Type your task or 'exit' to quit.",
        title="Orkit"
    ))
    
    router = CouncilRouter(default_model=model)
    
    while True:
        try:
            user_input = console.input("\n[bold]You:[/] ")
            
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[yellow]Goodbye![/]")
                break
            
            if not user_input.strip():
                continue
            
            # Route the task
            route = router.analyze_task(user_input)
            console.print(f"[dim]→ Routed to: {route.crew_type.value} (complexity: {route.complexity:.2f})[/]")
            
            # Execute based on route
            if route.crew_type.value == "planning":
                crew = PlanningCrew(model=route.model)
            else:
                crew = CodingCrew(model=route.model)
            
            result = asyncio.run(crew.execute(user_input))
            console.print(f"\n[bold cyan]Orkit:[/] {result}")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


def main() -> int:
    """Main entry point."""
    try:
        cli()
        return 0
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/]")
        return 1


if __name__ == "__main__":
    main()
