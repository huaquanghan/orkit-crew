"""Council Router for task routing and complexity analysis."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import re


class CrewType(Enum):
    """Types of crews available."""
    PLANNING = "planning"
    CODING = "coding"
    CHAT = "chat"


class RoutingStrategy(Enum):
    """Routing strategies."""
    FAST = "fast"      # Quick, simple tasks
    DEEP = "deep"      # Complex, multi-step tasks
    LOCAL = "local"    # Local-only, no external calls


@dataclass
class RouteDecision:
    """Decision made by the router."""
    crew_type: CrewType
    strategy: RoutingStrategy
    model: str
    complexity: float  # 0.0 to 1.0
    estimated_cost: float  # Estimated token cost
    reasoning: str
    context_window: int


class CouncilRouter:
    """Router that analyzes tasks and decides which crew to use."""
    
    # Complexity indicators
    COMPLEX_KEYWORDS = [
        "architecture", "design", "system", "microservice", "database",
        "scalable", "distributed", "integration", "workflow", "pipeline",
        "strategy", "roadmap", "plan", "framework", "infrastructure",
    ]
    
    CODING_KEYWORDS = [
        "code", "implement", "function", "class", "api", "endpoint",
        "script", "module", "library", "refactor", "debug", "test",
        "generate", "write", "create file", "build app",
    ]
    
    SIMPLE_KEYWORDS = [
        "hello", "hi", "help", "what", "how", "explain", "define",
        "simple", "quick", "brief", "summary",
    ]
    
    def __init__(self, default_model: str = "planno"):
        self.default_model = default_model
        self.context_windows = {
            "planno": 128000,
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "claude-3": 200000,
        }
    
    def analyze_complexity(self, task: str) -> float:
        """Analyze task complexity (0.0 = simple, 1.0 = very complex)."""
        task_lower = task.lower()
        complexity_score = 0.0
        
        # Length factor
        word_count = len(task.split())
        if word_count > 50:
            complexity_score += 0.2
        elif word_count > 20:
            complexity_score += 0.1
        
        # Keyword analysis
        complex_matches = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in task_lower)
        complexity_score += min(complex_matches * 0.1, 0.3)
        
        # Question count (more questions = more complex)
        question_count = task.count("?")
        complexity_score += min(question_count * 0.05, 0.15)
        
        # Multi-step indicators
        step_indicators = ["step", "first", "then", "next", "finally", "after"]
        step_matches = sum(1 for ind in step_indicators if ind in task_lower)
        complexity_score += min(step_matches * 0.05, 0.15)
        
        return min(complexity_score, 1.0)
    
    def detect_crew_type(self, task: str) -> CrewType:
        """Detect which crew type is best suited for the task."""
        task_lower = task.lower()
        
        coding_score = sum(1 for kw in self.CODING_KEYWORDS if kw in task_lower)
        complex_score = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in task_lower)
        
        if coding_score > 0:
            return CrewType.CODING
        elif complex_score >= 2:
            return CrewType.PLANNING
        else:
            return CrewType.CHAT
    
    def estimate_cost(self, task: str, complexity: float) -> float:
        """Estimate token cost based on task and complexity."""
        base_cost = len(task.split()) * 1.5  # Input tokens
        output_estimate = 500 + (complexity * 1500)  # Output tokens
        return base_cost + output_estimate
    
    def select_strategy(self, complexity: float, crew_type: CrewType) -> RoutingStrategy:
        """Select routing strategy based on complexity."""
        if complexity < 0.3 and crew_type == CrewType.CODING:
            return RoutingStrategy.FAST
        elif complexity > 0.6:
            return RoutingStrategy.DEEP
        else:
            return RoutingStrategy.FAST
    
    def select_model(self, strategy: RoutingStrategy, crew_type: CrewType) -> str:
        """Select appropriate model based on strategy and crew type."""
        if strategy == RoutingStrategy.DEEP or crew_type == CrewType.PLANNING:
            return self.default_model  # Use best available
        elif strategy == RoutingStrategy.FAST:
            return self.default_model  # Could use lighter model
        else:
            return self.default_model
    
    def analyze_task(self, task: str) -> RouteDecision:
        """Analyze a task and return routing decision."""
        complexity = self.analyze_complexity(task)
        crew_type = self.detect_crew_type(task)
        strategy = self.select_strategy(complexity, crew_type)
        model = self.select_model(strategy, crew_type)
        estimated_cost = self.estimate_cost(task, complexity)
        
        # Generate reasoning
        reasoning_parts = [
            f"Detected crew type: {crew_type.value}",
            f"Complexity score: {complexity:.2f}",
        ]
        
        if complexity < 0.3:
            reasoning_parts.append("Low complexity - using fast strategy")
        elif complexity > 0.7:
            reasoning_parts.append("High complexity - using deep strategy")
        else:
            reasoning_parts.append("Medium complexity - balanced approach")
        
        return RouteDecision(
            crew_type=crew_type,
            strategy=strategy,
            model=model,
            complexity=complexity,
            estimated_cost=estimated_cost,
            reasoning="; ".join(reasoning_parts),
            context_window=self.context_windows.get(model, 128000),
        )
    
    def should_use_planning(self, task: str) -> bool:
        """Quick check if task needs planning crew."""
        decision = self.analyze_task(task)
        return decision.crew_type == CrewType.PLANNING
    
    def should_use_coding(self, task: str) -> bool:
        """Quick check if task needs coding crew."""
        decision = self.analyze_task(task)
        return decision.crew_type == CrewType.CODING
