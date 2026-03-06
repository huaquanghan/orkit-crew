# Orkit Crew - Complete Integration & Usage Guide

> Multi-Agent AI System for Intelligent Task Routing, Planning & Code Generation

---

## 📑 Table of Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Integration Guide](#4-integration-guide)
5. [Usage Guide](#5-usage-guide)
6. [API Reference](#6-api-reference)
7. [Examples](#7-examples)
8. [Troubleshooting](#8-troubleshooting)
9. [Best Practices](#9-best-practices)

---

## 1. Overview

### What is Orkit Crew?

Orkit Crew is a sophisticated **multi-agent AI system** designed to intelligently route, plan, and execute complex software development tasks. It orchestrates multiple specialized AI agents working together to deliver high-quality code solutions.

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Orkit Crew Architecture                 │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐                                           │
│  │   Council    │  ← Routes tasks to appropriate crews      │
│  │   Router     │                                           │
│  └──────┬───────┘                                           │
│         │                                                   │
│    ┌────┴────┐                                              │
│    ▼         ▼                                              │
│ ┌────────┐ ┌────────┐                                       │
│ │Planning│ │ Coding │                                       │
│ │ Crew   │ │ Crew   │                                       │
│ └───┬────┘ └───┬────┘                                       │
│     │          │                                            │
│     ▼          ▼                                            │
│ ┌────────────────────┐                                      │
│ │   Planno Gateway   │  ← Unified LLM Client                │
│ └────────────────────┘                                      │
│     │          │                                            │
│     ▼          ▼                                            │
│ ┌─────────────────────────────────────────┐                 │
│ │         Multi-layer Memory              │                 │
│ │  ┌─────────┐ ┌─────────┐ ┌─────────┐   │                 │
│ │  │  Redis  │ │ Qdrant  │ │Markdown │   │                 │
│ │  │ (Cache) │ │(Vector) │ │(Long-term)│  │                 │
│ │  └─────────┘ └─────────┘ └─────────┘   │                 │
│ └─────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Use Cases

| Use Case | Description |
|----------|-------------|
| **Feature Development** | Break down complex features into actionable tasks |
| **Code Generation** | Generate production-ready code with proper architecture |
| **Refactoring** | Plan and execute large-scale refactoring projects |
| **Bug Fixing** | Analyze, plan, and implement bug fixes systematically |
| **Code Review** | Automated code analysis and improvement suggestions |
| **Documentation** | Generate technical documentation from code |
| **Integration Tasks** | Plan and implement third-party integrations |

### Key Features

- 🎯 **Intelligent Routing** - Council Router directs tasks to the right crew
- 📋 **Smart Planning** - Planning Crew breaks down complex tasks
- 💻 **Code Generation** - Coding Crew produces production-quality code
- 🧠 **Multi-layer Memory** - Redis caching, Qdrant vector search, Markdown persistence
- 🔌 **Pluggable Architecture** - Easy integration with existing systems
- ⚡ **Async Processing** - Non-blocking task execution
- 📊 **Progress Tracking** - Real-time task status and progress

---

## 2. Installation

### Prerequisites

- Python 3.10+
- Redis 6.0+ (for caching)
- Qdrant (for vector storage)
- Docker & Docker Compose (optional, for containerized deployment)

### 2.1 Local Installation

#### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/orkit-crew.git
cd orkit-crew
```

#### Step 2: Create Virtual Environment

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### Step 3: Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies (optional)
pip install -r requirements-dev.txt
```

#### Step 4: Verify Installation

```bash
python -c "from orkit_crew import CouncilRouter; print('✓ Orkit Crew installed successfully')"
```

### 2.2 Docker Installation

#### Quick Start with Docker Compose

```bash
# Clone repository
git clone https://github.com/your-org/orkit-crew.git
cd orkit-crew

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

#### Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  orkit-crew:
    build: .
    container_name: orkit-crew
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis
      - qdrant
    volumes:
      - ./data:/app/data
      - ./memory:/app/memory

  redis:
    image: redis:7-alpine
    container_name: orkit-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  qdrant:
    image: qdrant/qdrant:latest
    container_name: orkit-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  redis_data:
  qdrant_data:
```

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/memory /app/logs

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "orkit_crew.server"]
```

### 2.3 Development Installation

```bash
# Clone with all branches
git clone --recursive https://github.com/your-org/orkit-crew.git
cd orkit-crew

# Install in editable mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/
```

---

## 3. Configuration

### 3.1 Environment Variables

Create a `.env` file in your project root:

```bash
# Core Settings
ORKIT_ENV=development
ORKIT_LOG_LEVEL=INFO
ORKIT_WORKERS=4

# LLM Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7

# Alternative LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-opus-20240229

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
REDIS_SSL=false

# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=orkit_memory

# Memory Settings
MEMORY_TTL=86400
VECTOR_DIMENSION=1536
SIMILARITY_THRESHOLD=0.85

# Server Settings
HOST=0.0.0.0
PORT=8000
API_PREFIX=/api/v1

# Security
API_KEY_HEADER=X-API-Key
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 3.2 Configuration File

Create `config.yaml` for advanced configuration:

```yaml
# config.yaml
orkit:
  environment: production
  log_level: INFO
  
  council_router:
    routing_strategy: intelligent
    fallback_enabled: true
    confidence_threshold: 0.8
    
  planning_crew:
    max_iterations: 5
    planning_mode: hierarchical
    include_architecture: true
    
  coding_crew:
    code_style: pep8
    include_tests: true
    review_enabled: true
    
  planno_gateway:
    provider: openai
    timeout: 60
    retry_attempts: 3
    
  memory:
    cache_ttl: 86400
    vector_search_top_k: 10
    persistence_enabled: true
    
  crews:
    - name: planning
      agents:
        - task_planner
        - architect
      max_concurrent: 2
      
    - name: coding
      agents:
        - code_generator
        - code_reviewer
      max_concurrent: 3
```

### 3.3 Programmatic Configuration

```python
from orkit_crew import OrkitCrew, Config

# Create configuration programmatically
config = Config(
    environment="production",
    log_level="INFO",
    redis_url="redis://localhost:6379",
    qdrant_url="http://localhost:6333",
    openai_api_key="sk-...",
    crews={
        "planning": {
            "max_iterations": 5,
            "planning_mode": "hierarchical"
        },
        "coding": {
            "code_style": "pep8",
            "include_tests": True
        }
    }
)

# Initialize Orkit Crew with config
orkit = OrkitCrew(config=config)
```

---

## 4. Integration Guide

### 4.1 Integration into Existing Project

#### Basic Integration

```python
# your_project/ai_integration.py
from orkit_crew import CouncilRouter, TaskRequest

class AIIntegration:
    def __init__(self):
        self.router = CouncilRouter()
    
    async def generate_feature(self, description: str, context: dict = None):
        """Generate a new feature using Orkit Crew."""
        request = TaskRequest(
            task_type="feature_development",
            description=description,
            context=context or {},
            priority="high"
        )
        
        # Route to appropriate crew
        result = await self.router.route(request)
        return result
    
    async def refactor_code(self, file_path: str, improvements: list):
        """Refactor existing code."""
        request = TaskRequest(
            task_type="refactoring",
            description=f"Refactor {file_path}",
            context={
                "file_path": file_path,
                "improvements": improvements
            }
        )
        return await self.router.route(request)

# Usage
integration = AIIntegration()
result = await integration.generate_feature(
    description="Create a user authentication system with JWT",
    context={"framework": "fastapi", "database": "postgresql"}
)
```

#### FastAPI Integration

```python
# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from orkit_crew import CouncilRouter, TaskRequest

app = FastAPI(title="My API with Orkit Crew")
router = CouncilRouter()

class FeatureRequest(BaseModel):
    description: str
    context: dict = {}
    priority: str = "medium"

@app.post("/ai/generate-feature")
async def generate_feature(request: FeatureRequest):
    """Generate a feature using AI."""
    try:
        task = TaskRequest(
            task_type="feature_development",
            description=request.description,
            context=request.context,
            priority=request.priority
        )
        
        result = await router.route(task)
        
        return {
            "status": "success",
            "task_id": result.task_id,
            "plan": result.plan,
            "code": result.code,
            "tests": result.tests
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/task/{task_id}")
async def get_task_status(task_id: str):
    """Get status of an AI task."""
    status = await router.get_task_status(task_id)
    return status
```

#### Django Integration

```python
# views.py
from django.http import JsonResponse
from django.views import View
from orkit_crew import CouncilRouter

class AIFeatureView(View):
    router = CouncilRouter()
    
    async def post(self, request):
        data = json.loads(request.body)
        
        task_request = TaskRequest(
            task_type="feature_development",
            description=data.get("description"),
            context=data.get("context", {})
        )
        
        result = await self.router.route(task_request)
        
        return JsonResponse({
            "task_id": result.task_id,
            "status": result.status,
            "deliverables": result.deliverables
        })
```

### 4.2 OpenClaw Integration

Orkit Crew can be seamlessly integrated with OpenClaw for enhanced agent capabilities.

#### Setup

```python
# openclaw_integration.py
from openclaw import OpenClaw
from orkit_crew import CouncilRouter

class OpenClawOrkitBridge:
    def __init__(self):
        self.openclaw = OpenClaw()
        self.router = CouncilRouter()
    
    async def process_openclaw_task(self, task_data: dict):
        """Process tasks from OpenClaw through Orkit Crew."""
        
        # Convert OpenClaw task to Orkit format
        task_request = TaskRequest(
            task_type=task_data.get("type", "general"),
            description=task_data.get("description"),
            context={
                "source": "openclaw",
                **task_data.get("context", {})
            },
            priority=task_data.get("priority", "medium")
        )
        
        # Route through Council Router
        result = await self.router.route(task_request)
        
        # Format response for OpenClaw
        return {
            "success": True,
            "openclaw_task_id": task_data.get("id"),
            "orkit_task_id": result.task_id,
            "output": {
                "plan": result.plan,
                "code": result.code,
                "documentation": result.documentation
            }
        }
```

#### OpenClaw Skill Configuration

```yaml
# ~/.openclaw/skills/orkit-crew/skill.yaml
name: orkit-crew
description: Orkit Crew multi-agent integration
version: 1.0.0

commands:
  generate:
    description: Generate code using Orkit Crew
    handler: orkit_crew_openclaw:generate_handler
    
  plan:
    description: Create development plan
    handler: orkit_crew_openclaw:plan_handler
    
  refactor:
    description: Refactor existing code
    handler: orkit_crew_openclaw:refactor_handler

config:
  orkit_endpoint: http://localhost:8000
  api_key: ${ORKIT_API_KEY}
```

#### Usage in OpenClaw

```bash
# Generate feature
openclaw orkit-crew generate "Create REST API for user management"

# Create development plan
openclaw orkit-crew plan "Build microservices architecture"

# Refactor code
openclaw orkit-crew refactor --file src/main.py --target "improve performance"
```

### 4.3 Integration with Other Systems

#### CI/CD Pipeline Integration

```yaml
# .github/workflows/orkit-crew.yml
name: AI Code Generation

on:
  issues:
    types: [labeled]

jobs:
  generate-code:
    if: contains(github.event.issue.labels.*.name, 'ai-generate')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Orkit Crew
        run: |
          pip install orkit-crew
          
      - name: Generate Code
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python -m orkit_crew.cli generate \
            --issue ${{ github.event.issue.number }} \
            --output ./generated
            
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          title: "AI Generated: ${{ github.event.issue.title }}"
          body: "Closes #${{ github.event.issue.number }}"
```

#### Slack Integration

```python
# slack_bot.py
from slack_bolt.async_app import AsyncApp
from orkit_crew import CouncilRouter

app = AsyncApp()
router = CouncilRouter()

@app.command("/generate")
async def handle_generate(ack, command, say):
    await ack()
    
    request = TaskRequest(
        task_type="feature_development",
        description=command["text"],
        context={"source": "slack"}
    )
    
    result = await router.route(request)
    
    await say(f"✅ Task created: `{result.task_id}`\n"
              f"📋 Status: {result.status}\n"
              f"🔗 View details: {result.dashboard_url}")
```

---

## 5. Usage Guide

### 5.1 Council Router

The Council Router is the entry point that intelligently routes tasks to the appropriate crew.

```python
from orkit_crew import CouncilRouter, TaskRequest, TaskType

# Initialize router
router = CouncilRouter()

# Create a task request
task = TaskRequest(
    task_type=TaskType.FEATURE_DEVELOPMENT,
    description="Create a user authentication system",
    context={
        "framework": "fastapi",
        "database": "postgresql",
        "requirements": ["JWT tokens", "refresh tokens", "role-based access"]
    },
    priority="high",
    deadline="2024-12-31"
)

# Route the task
result = await router.route(task)

# Check result
print(f"Task ID: {result.task_id}")
print(f"Assigned Crew: {result.crew}")
print(f"Status: {result.status}")
```

#### Routing Strategies

```python
# Intelligent routing (default)
router = CouncilRouter(strategy="intelligent")

# Rule-based routing
router = CouncilRouter(strategy="rule_based")

# Custom routing function
def custom_router(task: TaskRequest) -> str:
    if "database" in task.description.lower():
        return "database_crew"
    return "general_crew"

router = CouncilRouter(strategy=custom_router)
```

### 5.2 Planning Crew

The Planning Crew breaks down complex tasks into actionable steps.

```python
from orkit_crew.crews import PlanningCrew

# Initialize planning crew
planning = PlanningCrew()

# Create a development plan
plan = await planning.create_plan(
    description="Build e-commerce checkout system",
    context={
        "payment_providers": ["stripe", "paypal"],
        "features": ["cart", "checkout", "order tracking"],
        "tech_stack": ["fastapi", "react", "postgresql"]
    }
)

# Access plan components
print(f"Architecture: {plan.architecture}")
print(f"Tasks: {plan.tasks}")
print(f"Dependencies: {plan.dependencies}")
print(f"Estimates: {plan.time_estimates}")
```

#### Task Planner Agent

```python
from orkit_crew.agents import TaskPlanner

planner = TaskPlanner()

# Break down a feature into tasks
tasks = await planner.breakdown(
    feature="Implement user authentication",
    constraints={
        "time": "2 weeks",
        "team_size": 2,
        "must_have": ["JWT", "OAuth", "2FA"]
    }
)

for task in tasks:
    print(f"- {task.name}: {task.description}")
    print(f"  Estimated: {task.estimated_hours}h")
```

#### Architect Agent

```python
from orkit_crew.agents import Architect

architect = Architect()

# Design system architecture
architecture = await architect.design(
    requirements=[
        "Handle 10k concurrent users",
        "99.9% uptime",
        "Sub-100ms response time"
    ],
    constraints={
        "budget": "$500/month",
        "team_expertise": ["python", "aws"]
    }
)

print(f"Architecture Diagram: {architecture.diagram}")
print(f"Tech Stack: {architecture.tech_stack}")
print(f"Infrastructure: {architecture.infrastructure}")
```

### 5.3 Coding Crew

The Coding Crew generates production-ready code.

```python
from orkit_crew.crews import CodingCrew

# Initialize coding crew
coding = CodingCrew()

# Generate code from plan
code_result = await coding.generate(
    plan=plan,
    specifications={
        "language": "python",
        "framework": "fastapi",
        "style_guide": "pep8",
        "include_tests": True,
        "include_docs": True
    }
)

# Access generated code
print(f"Code Files: {code_result.files}")
print(f"Tests: {code_result.tests}")
print(f"Documentation: {code_result.documentation}")
```

#### Code Generator Agent

```python
from orkit_crew.agents import CodeGenerator

generator = CodeGenerator(
    style="pep8",
    include_type_hints=True,
    include_docstrings=True
)

# Generate specific component
component = await generator.generate(
    component_type="api_endpoint",
    specification={
        "path": "/api/users",
        "method": "POST",
        "request_model": "UserCreate",
        "response_model": "UserResponse",
        "authentication": "jwt"
    }
)

print(component.code)
```

### 5.4 Planno Gateway

The Planno Gateway is the unified LLM client.

```python
from orkit_crew import PlannoGateway

# Initialize gateway
gateway = PlannoGateway(
    provider="openai",
    model="gpt-4",
    temperature=0.7
)

# Generate completion
response = await gateway.complete(
    prompt="Explain the concept of dependency injection",
    max_tokens=500
)

# Chat completion
messages = [
    {"role": "system", "content": "You are a Python expert"},
    {"role": "user", "content": "How do I use async/await?"}
]
response = await gateway.chat(messages)

# Streaming response
async for chunk in gateway.stream_complete("Tell me a story"):
    print(chunk, end="")
```

### 5.5 Multi-layer Memory

```python
from orkit_crew.memory import MemoryManager

# Initialize memory
memory = MemoryManager()

# Store in short-term cache (Redis)
await memory.cache.set(
    key="user:123:preferences",
    value={"theme": "dark", "language": "vi"},
    ttl=3600
)

# Store in vector memory (Qdrant)
await memory.vector.store(
    text="Important architectural decision: using microservices",
    metadata={"project": "myapp", "type": "decision"}
)

# Search vector memory
results = await memory.vector.search(
    query="architecture decisions",
    top_k=5
)

# Store in long-term memory (Markdown)
await memory.persistent.save(
    title="API Design Guidelines",
    content="# API Design Guidelines\n\n1. Use RESTful principles...",
    tags=["api", "guidelines"]
)
```

---

## 6. API Reference

### 6.1 Core Classes

#### CouncilRouter

```python
class CouncilRouter:
    """Routes tasks to appropriate crews."""
    
    def __init__(
        self,
        strategy: str | Callable = "intelligent",
        fallback_enabled: bool = True,
        confidence_threshold: float = 0.8
    ):
        """
        Initialize the Council Router.
        
        Args:
            strategy: Routing strategy ("intelligent", "rule_based", or callable)
            fallback_enabled: Whether to use fallback routing
            confidence_threshold: Minimum confidence for routing decision
        """
    
    async def route(self, request: TaskRequest) -> TaskResult:
        """
        Route a task to the appropriate crew.
        
        Args:
            request: The task request to route
            
        Returns:
            TaskResult containing the execution results
        """
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """Get the current status of a task."""
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
```

#### TaskRequest

```python
@dataclass
class TaskRequest:
    """Request for task execution."""
    
    task_type: TaskType | str
    description: str
    context: dict = field(default_factory=dict)
    priority: str = "medium"  # low, medium, high, critical
    deadline: str | None = None
    metadata: dict = field(default_factory=dict)
```

#### TaskResult

```python
@dataclass
class TaskResult:
    """Result of task execution."""
    
    task_id: str
    crew: str
    status: str  # pending, running, completed, failed
    plan: Plan | None = None
    code: CodeOutput | None = None
    tests: list[Test] = field(default_factory=list)
    documentation: str = ""
    logs: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
```

### 6.2 Crew Classes

#### PlanningCrew

```python
class PlanningCrew:
    """Crew responsible for task planning and architecture."""
    
    def __init__(
        self,
        max_iterations: int = 5,
        planning_mode: str = "hierarchical",
        include_architecture: bool = True
    ):
        """
        Initialize Planning Crew.
        
        Args:
            max_iterations: Maximum planning refinement iterations
            planning_mode: Planning approach ("hierarchical", "sequential", "parallel")
            include_architecture: Whether to include architecture design
        """
    
    async def create_plan(
        self,
        description: str,
        context: dict = None
    ) -> Plan:
        """Create a development plan."""
    
    async def refine_plan(
        self,
        plan: Plan,
        feedback: str
    ) -> Plan:
        """Refine an existing plan based on feedback."""
```

#### CodingCrew

```python
class CodingCrew:
    """Crew responsible for code generation."""
    
    def __init__(
        self,
        code_style: str = "pep8",
        include_tests: bool = True,
        include_docs: bool = True,
        review_enabled: bool = True
    ):
        """
        Initialize Coding Crew.
        
        Args:
            code_style: Code style guide to follow
            include_tests: Whether to generate tests
            include_docs: Whether to generate documentation
            review_enabled: Whether to enable code review
        """
    
    async def generate(
        self,
        plan: Plan,
        specifications: dict = None
    ) -> CodeOutput:
        """Generate code from a plan."""
    
    async def review_code(
        self,
        code: CodeOutput
    ) -> CodeReview:
        """Review generated code."""
```

### 6.3 Memory Classes

#### MemoryManager

```python
class MemoryManager:
    """Manages multi-layer memory system."""
    
    def __init__(
        self,
        redis_url: str = None,
        qdrant_url: str = None,
        memory_dir: str = "./memory"
    ):
        """Initialize memory manager."""
    
    @property
    def cache(self) -> CacheLayer:
        """Access Redis cache layer."""
    
    @property
    def vector(self) -> VectorLayer:
        """Access Qdrant vector layer."""
    
    @property
    def persistent(self) -> PersistentLayer:
        """Access Markdown persistent layer."""
```

### 6.4 HTTP API Endpoints

#### REST API

```http
### Create Task
POST /api/v1/tasks
Content-Type: application/json

{
  "task_type": "feature_development",
  "description": "Create user authentication",
  "context": {
    "framework": "fastapi"
  },
  "priority": "high"
}

### Get Task Status
GET /api/v1/tasks/{task_id}

### List Tasks
GET /api/v1/tasks?status=running&limit=10

### Cancel Task
DELETE /api/v1/tasks/{task_id}

### Get Crews
GET /api/v1/crews

### Get Memory Stats
GET /api/v1/memory/stats
```

---

## 7. Examples

### 7.1 Complete Feature Development

```python
import asyncio
from orkit_crew import CouncilRouter, TaskRequest

async def develop_feature():
    """Complete example of feature development."""
    
    # Initialize router
    router = CouncilRouter()
    
    # Step 1: Create task request
    task = TaskRequest(
        task_type="feature_development",
        description="Build a REST API for blog posts with CRUD operations",
        context={
            "framework": "fastapi",
            "database": "postgresql",
            "orm": "sqlalchemy",
            "features": [
                "Create post",
                "Read post (with pagination)",
                "Update post",
                "Delete post",
                "List posts by author"
            ],
            "authentication": "jwt"
        },
        priority="high"
    )
    
    # Step 2: Route and execute
    print("🚀 Starting feature development...")
    result = await router.route(task)
    
    # Step 3: Process results
    print(f"\n✅ Task completed: {result.task_id}")
    print(f"Status: {result.status}")
    
    if result.plan:
        print(f"\n📋 Plan created with {len(result.plan.tasks)} tasks")
        for t in result.plan.tasks:
            print(f"  - {t.name}: {t.estimated_hours}h")
    
    if result.code:
        print(f"\n💻 Code generated:")
        for file in result.code.files:
            print(f"  - {file.path} ({file.language})")
    
    if result.tests:
        print(f"\n🧪 Tests generated: {len(result.tests)}")
    
    # Step 4: Save results
    result.save_to_disk("./output/blog_api")
    print(f"\n💾 Results saved to ./output/blog_api")

# Run
asyncio.run(develop_feature())
```

### 7.2 Refactoring Project

```python
from orkit_crew import CouncilRouter, TaskRequest

async def refactor_legacy_code():
    """Example of refactoring legacy codebase."""
    
    router = CouncilRouter()
    
    # Analyze codebase first
    analyze_task = TaskRequest(
        task_type="code_analysis",
        description="Analyze legacy codebase for refactoring opportunities",
        context={
            "codebase_path": "./legacy_project",
            "target_improvements": [
                "reduce_complexity",
                "improve_test_coverage",
                "modernize_patterns"
            ]
        }
    )
    
    analysis = await router.route(analyze_task)
    
    # Create refactoring plan
    refactor_task = TaskRequest(
        task_type="refactoring",
        description="Refactor legacy codebase based on analysis",
        context={
            "analysis_results": analysis.to_dict(),
            "refactoring_strategy": "incremental",
            "preserve_behavior": True
        }
    )
    
    result = await router.route(refactor_task)
    return result
```

### 7.3 Batch Processing

```python
from orkit_crew import CouncilRouter
import asyncio

async def process_multiple_features():
    """Process multiple features concurrently."""
    
    router = CouncilRouter()
    
    features = [
        "User registration with email verification",
        "Password reset flow",
        "User profile management",
        "Admin dashboard"
    ]
    
    # Create all tasks
    tasks = [
        router.route(TaskRequest(
            task_type="feature_development",
            description=feature,
            context={"framework": "fastapi"}
        ))
        for feature in features
    ]
    
    # Execute concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for feature, result in zip(features, results):
        if isinstance(result, Exception):
            print(f"❌ {feature}: Failed - {result}")
        else:
            print(f"✅ {feature}: Completed - {result.task_id}")
    
    return results
```

### 7.4 Custom Agent Integration

```python
from orkit_crew import CouncilRouter
from orkit_crew.crews import BaseCrew

class DocumentationCrew(BaseCrew):
    """Custom crew for documentation generation."""
    
    async def execute(self, request: TaskRequest) -> TaskResult:
        """Generate documentation."""
        
        # Extract code from context
        code = request.context.get("code", "")
        doc_type = request.context.get("doc_type", "api")
        
        # Generate documentation
        if doc_type == "api":
            docs = await self.generate_api_docs(code)
        elif doc_type == "readme":
            docs = await self.generate_readme(code)
        else:
            docs = await self.generate_general_docs(code)
        
        return TaskResult(
            task_id=self.generate_id(),
            crew="documentation",
            status="completed",
            documentation=docs
        )

# Register custom crew
router = CouncilRouter()
router.register_crew("documentation", DocumentationCrew())

# Use custom crew
result = await router.route(TaskRequest(
    task_type="documentation",
    description="Generate API documentation",
    context={"code": source_code, "doc_type": "api"}
))
```

### 7.5 Memory-Enhanced Workflow

```python
from orkit_crew import CouncilRouter, MemoryManager

async def memory_enhanced_workflow():
    """Example using multi-layer memory."""
    
    router = CouncilRouter()
    memory = MemoryManager()
    
    # Check if similar task was done before
    similar = await memory.vector.search(
        query="user authentication system",
        top_k=3
    )
    
    if similar:
        print(f"Found {len(similar)} similar past tasks")
        context = {
            "previous_implementations": [s.metadata for s in similar]
        }
    else:
        context = {}
    
    # Execute task
    result = await router.route(TaskRequest(
        task_type="feature_development",
        description="Create OAuth2 authentication",
        context=context
    ))
    
    # Store in memory for future reference
    await memory.vector.store(
        text=f"OAuth2 authentication implementation: {result.code.summary}",
        metadata={
            "task_id": result.task_id,
            "type": "authentication",
            "framework": "fastapi"
        }
    )
    
    # Save detailed documentation
    await memory.persistent.save(
        title=f"OAuth2 Implementation - {result.task_id}",
        content=result.documentation,
        tags=["oauth2", "authentication", "fastapi"]
    )
    
    return result
```

---

## 8. Troubleshooting

### 8.1 Common Issues

#### Issue: Redis Connection Failed

```
Error: Connection refused to Redis at localhost:6379
```

**Solutions:**

```bash
# Check if Redis is running
redis-cli ping

# Start Redis
redis-server

# Or using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Verify connection
python -c "import redis; r = redis.Redis(); print(r.ping())"
```

#### Issue: Qdrant Connection Failed

```
Error: Cannot connect to Qdrant at http://localhost:6333
```

**Solutions:**

```bash
# Start Qdrant with Docker
docker run -d -p 6333:6333 qdrant/qdrant

# Verify health
curl http://localhost:6333/healthz

# Check collections
curl http://localhost:6333/collections
```

#### Issue: LLM API Rate Limit

```
Error: Rate limit exceeded for OpenAI API
```

**Solutions:**

```python
# Add rate limiting
from orkit_crew import PlannoGateway

gateway = PlannoGateway(
    provider="openai",
    rate_limit_requests=50,  # requests per minute
    rate_limit_tokens=100000  # tokens per minute
)

# Or implement exponential backoff
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
async def generate_with_retry():
    return await gateway.complete("Your prompt")
```

#### Issue: Task Routing Fails

```
Error: No crew found for task type 'unknown_type'
```

**Solutions:**

```python
# Enable fallback routing
router = CouncilRouter(fallback_enabled=True)

# Or register a default crew
router.register_fallback_crew(GeneralCrew())

# Check available crews
print(router.list_crews())
```

#### Issue: Memory Storage Errors

```
Error: Failed to store in vector memory
```

**Solutions:**

```python
# Check Qdrant collection exists
from qdrant_client import QdrantClient

client = QdrantClient("localhost", port=6333)

# Create collection if missing
client.create_collection(
    collection_name="orkit_memory",
    vectors_config={"size": 1536, "distance": "Cosine"}
)

# Or disable vector memory temporarily
memory = MemoryManager(
    redis_url="redis://localhost:6379",
    qdrant_url=None  # Disable vector memory
)
```

### 8.2 Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or configure via environment
import os
os.environ["ORKIT_LOG_LEVEL"] = "DEBUG"

# Initialize with debug
from orkit_crew import CouncilRouter

router = CouncilRouter(debug=True)

# Get detailed execution logs
result = await router.route(task)
print(result.logs)
```

### 8.3 Performance Issues

```python
# Optimize for performance
router = CouncilRouter(
    max_concurrent_tasks=10,
    cache_enabled=True,
    cache_ttl=3600
)

# Use batch processing
results = await router.route_batch(tasks, batch_size=5)

# Profile execution
import cProfile
profiler = cProfile.Profile()
profiler.enable()

result = await router.route(task)

profiler.disable()
profiler.print_stats(sort='cumulative')
```

---

## 9. Best Practices

### 9.1 Task Design

```python
# ✅ Good: Clear, specific task
TaskRequest(
    task_type="feature_development",
    description="Create REST API endpoint for user registration",
    context={
        "framework": "fastapi",
        "fields": ["email", "password", "name"],
        "validation_rules": {
            "email": "valid email format",
            "password": "min 8 characters"
        }
    }
)

# ❌ Bad: Vague task
TaskRequest(
    task_type="feature_development",
    description="Build user stuff"
)
```

### 9.2 Context Management

```python
# ✅ Good: Structured context
context = {
    "project": {
        "name": "MyApp",
        "version": "1.0.0",
        "tech_stack": ["fastapi", "postgresql"]
    },
    "requirements": [
        "JWT authentication",
        "Role-based access control"
    ],
    "constraints": {
        "max_response_time": "100ms",
        "budget": "$500/month"
    }
}

# ❌ Bad: Unstructured context
context = {
    "some_info": "...",
    "random_data": "..."
}
```

### 9.3 Error Handling

```python
# ✅ Good: Proper error handling
from orkit_crew.exceptions import TaskFailedError, RoutingError

try:
    result = await router.route(task)
except RoutingError as e:
    logger.error(f"Routing failed: {e}")
    # Fallback to manual assignment
    result = await manual_assignment(task)
except TaskFailedError as e:
    logger.error(f"Task failed: {e}")
    # Retry with different parameters
    result = await retry_task(task)
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### 9.4 Memory Optimization

```python
# ✅ Good: Efficient memory usage
memory = MemoryManager()

# Cache frequently accessed data
await memory.cache.set("config", config, ttl=3600)

# Store important decisions in vector memory
await memory.vector.store(
    text="Decision: Using microservices architecture",
    metadata={"type": "decision", "impact": "high"}
)

# Persist critical documentation
await memory.persistent.save(
    title="Architecture Decision Records",
    content=adr_content,
    tags=["adr", "architecture"]
)
```

### 9.5 Security Best Practices

```python
# ✅ Good: Secure configuration
from orkit_crew import Config

config = Config(
    # Use environment variables for secrets
    openai_api_key=os.environ["OPENAI_API_KEY"],
    
    # Enable API authentication
    api_key_required=True,
    
    # Restrict allowed hosts
    allowed_hosts=["api.myapp.com"],
    
    # Enable request validation
    validate_requests=True,
    
    # Sanitize outputs
    sanitize_outputs=True
)

# Validate inputs
from pydantic import BaseModel, validator

class SecureTaskRequest(BaseModel):
    description: str
    
    @validator('description')
    def no_sensitive_data(cls, v):
        # Prevent prompt injection
        forbidden = ["ignore previous", "system prompt", "password"]
        for word in forbidden:
            if word in v.lower():
                raise ValueError(f"Description contains forbidden word: {word}")
        return v
```

### 9.6 Monitoring & Observability

```python
# ✅ Good: Add observability
from prometheus_client import Counter, Histogram
import structlog

logger = structlog.get_logger()

# Metrics
task_counter = Counter('orkit_tasks_total', 'Total tasks', ['crew', 'status'])
task_duration = Histogram('orkit_task_duration_seconds', 'Task duration')

class ObservableRouter(CouncilRouter):
    async def route(self, request):
        start_time = time.time()
        
        logger.info(
            "task_started",
            task_type=request.task_type,
            task_id=request.id
        )
        
        try:
            result = await super().route(request)
            task_counter.labels(crew=result.crew, status="success").inc()
            
            logger.info(
                "task_completed",
                task_id=result.task_id,
                duration=time.time() - start_time
            )
            
            return result
        except Exception as e:
            task_counter.labels(crew="unknown", status="failed").inc()
            logger.error("task_failed", error=str(e))
            raise
        finally:
            task_duration.observe(time.time() - start_time)
```

### 9.7 Testing

```python
# ✅ Good: Test your integration
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_router():
    router = CouncilRouter()
    router.route = AsyncMock(return_value=TaskResult(
        task_id="test-123",
        crew="planning",
        status="completed"
    ))
    return router

async def test_feature_generation(mock_router):
    result = await mock_router.route(TaskRequest(
        task_type="feature_development",
        description="Test feature"
    ))
    
    assert result.status == "completed"
    assert result.task_id == "test-123"

# Integration test
@pytest.mark.integration
async def test_end_to_end():
    router = CouncilRouter()
    
    result = await router.route(TaskRequest(
        task_type="feature_development",
        description="Create a simple function",
        context={"language": "python"}
    ))
    
    assert result.code is not None
    assert len(result.code.files) > 0
```

---

## 📚 Additional Resources

- **GitHub Repository**: https://github.com/your-org/orkit-crew
- **Documentation**: https://orkit-crew.readthedocs.io
- **API Reference**: https://orkit-crew.readthedocs.io/api
- **Examples**: https://github.com/your-org/orkit-crew/tree/main/examples
- **Discord Community**: https://discord.gg/orkit-crew

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

---

## 📄 License

Orkit Crew is released under the MIT License. See [LICENSE](LICENSE) for details.

---

*Built with ❤️ by the Orkit Crew Team*
