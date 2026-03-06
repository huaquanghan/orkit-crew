"""Tests for core components."""

import pytest
from orkit_crew.core.router import CouncilRouter, CrewType, RoutingStrategy


def test_router_detects_coding_task():
    """Test that coding tasks are detected correctly."""
    router = CouncilRouter()
    
    decision = router.analyze_task("Create a Python function to parse JSON")
    assert decision.crew_type == CrewType.CODING


def test_router_detects_planning_task():
    """Test that planning tasks are detected correctly."""
    router = CouncilRouter()
    
    decision = router.analyze_task("Design a microservice architecture for e-commerce")
    assert decision.crew_type == CrewType.PLANNING


def test_complexity_analysis():
    """Test complexity scoring."""
    router = CouncilRouter()
    
    simple = router.analyze_complexity("Hello world")
    complex_task = router.analyze_complexity(
        "Design a distributed system with microservices, database sharding, "
        "and event-driven architecture for high scalability"
    )
    
    assert simple < complex_task
    assert 0.0 <= simple <= 1.0
    assert 0.0 <= complex_task <= 1.0
