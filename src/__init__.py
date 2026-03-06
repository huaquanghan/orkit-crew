"""
Changcomchien - Multi-Agent AI System

A multi-agent AI system built with CrewAI and Planno LLM gateway.
"""

__version__ = "0.1.0"

# Import main components for easier access
from .core import MemoryManager, Task, memory_manager, CouncilRouter, router
from .gateway import app, create_app

__all__ = [
    "MemoryManager",
    "Task",
    "memory_manager",
    "CouncilRouter",
    "router",
    "app",
    "create_app",
]
