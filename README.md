# Orkit Crew 🚀

AI Crew Orchestration System with Planno Gateway integration. Built with CrewAI for intelligent task routing and execution.

## Features

- 🤖 **Intelligent Routing**: Council Router analyzes tasks and routes to appropriate crews
- 🧠 **Multi-layer Memory**: Redis (short-term) + Qdrant (long-term) + Markdown (working memory)
- 👥 **Specialized Crews**: Planning Crew (Task Planner + Architect) and Coding Crew (Code Generator)
- 🌐 **Planno Gateway**: Async LLM client with streaming support
- 🐳 **Docker Ready**: Complete Docker Compose setup with Redis and Qdrant

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Orkit CLI                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    Council Router                              │
│         (Task Analysis → Route Decision)                     │
└───────────────┬───────────────────────┬─────────────────────┘
                │                       │
    ┌───────────▼──────────┐  ┌────────▼────────┐
    │   Planning Crew      │  │   Coding Crew   │
    │  - Task Planner      │  │  - Code Gen     │
    │  - Architect         │  │                 │
    └───────────┬──────────┘  └────────┬────────┘
                │                       │
    ┌───────────▼───────────────────────▼────────────┐
    │              Planno Gateway                     │
    │         (Async LLM Client)                      │
    └─────────────────────────────────────────────────┘
```

## Quick Start

### 1. Setup

```bash
# Clone and navigate to project
cd orkit-crew

# Run setup script
./scripts/setup.sh

# Or manually:
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file:

```env
PLANNO_URL=http://localhost:8787
PLANNO_API_KEY=your-api-key

REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

APP_ENV=development
LOG_LEVEL=INFO
```

### 3. Start Infrastructure

```bash
# Start Redis and Qdrant
docker-compose up -d redis qdrant

# Or start all services (including app)
docker-compose up -d
```

### 4. Run Orkit

```bash
# Show help
orkit --help

# Planning mode
orkit plan "Create a Python API for task management"

# Coding mode
orkit code "Generate a FastAPI endpoint for user authentication"

# Interactive chat
orkit chat
```

## CLI Commands

### `orkit plan <task>`
Run the Planning Crew to break down complex tasks.

```bash
orkit plan "Design a microservice architecture for e-commerce"
```

### `orkit code <task>`
Run the Coding Crew to generate code.

```bash
orkit code "Create a Python function to parse JSON with error handling"
```

### `orkit chat`
Interactive chat mode with automatic routing.

```bash
orkit chat
# Then type your tasks interactively
```

## Project Structure

```
orkit-crew/
├── docker-compose.yml          # Redis + Qdrant + App
├── Dockerfile
├── pyproject.toml              # Dependencies & scripts
├── .env.example                # Environment template
├── README.md
├── scripts/
│   └── setup.sh               # Setup script
├── src/orkit_crew/
│   ├── __init__.py
│   ├── main.py                # Entry point
│   ├── cli.py                 # CLI commands
│   ├── core/
│   │   ├── config.py          # Pydantic settings
│   │   ├── memory.py          # Redis + Qdrant integration
│   │   ├── router.py          # Council Router
│   │   └── state.py           # Task state machine
│   ├── crews/
│   │   ├── base.py            # BaseCrew class
│   │   ├── planning_crew.py   # Planning agents
│   │   └── coding_crew.py     # Coding agents
│   ├── gateway/
│   │   └── plano_client.py    # Planno LLM client
│   └── tools/
│       └── __init__.py        # Custom tools
└── tests/
```

## Core Components

### Council Router

Analyzes tasks and routes to appropriate crews:

```python
from orkit_crew.core.router import CouncilRouter

router = CouncilRouter()
decision = router.analyze_task("Create a Python API")
print(decision.crew_type)  # CrewType.CODING
print(decision.complexity)  # 0.45
```

### Memory Manager

Unified memory across layers:

```python
from orkit_crew.core.memory import MemoryManager

memory = MemoryManager()

# Session memory (Redis)
memory.store_session("session-123", {"user": "alice"})

# Long-term memory (Qdrant)
memory.store_memory("content", vector=[0.1, 0.2, ...])

# Working memory (Markdown)
memory.save_working_memory("plan", "# Project Plan\n...")
```

### Crews

**PlanningCrew**: Task Planner + Architect agents for complex planning tasks.

**CodingCrew**: Code Generator agent for implementation tasks.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/

# Type checking
mypy src/
```

## 🐳 Docker Support

### Quick Start

```bash
docker run huaquanghan/orkit-crew orkit --help
```

### Development

```bash
docker-compose up -d
```

[See full Docker docs](docs/DOCKER.md)

## Docker Commands

```bash
# Build image
docker-compose build

# Run with infrastructure
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop all
docker-compose down
```

## License

MIT
