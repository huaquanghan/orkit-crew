# Orkit Crew Architecture

## Overview

Orkit Crew là một AI Crew Orchestration System với kiến trúc phân tầng rõ ràng. Hệ thống được thiết kế để nhận request từ user, route đến crew phù hợp, và trả kết quả về thông qua Gateway.

## Mental Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER REQUEST                                    │
│                    (HTTP / API / CLI / WebSocket)                           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         GATEWAY (Entry Point)                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   HTTP API  │  │  WebSocket  │  │  CLI Handler│  │  Webhook    │ │   │
│  │  │   Server    │  │   Server    │  │             │  │  Handler    │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  │                                                                     │   │
│  │  Responsibilities:                                                  │   │
│  │  • Nhận request từ user qua nhiều channels                          │   │
│  │  • Authentication & Authorization                                   │   │
│  │  • Request validation                                               │   │
│  │  • Rate limiting                                                    │   │
│  │  • Gửi response về user                                             │   │
│  └────────────────────────────────────┬────────────────────────────────┘   │
└───────────────────────────────────────┼────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         COUNCIL ROUTER                               │   │
│  │                                                                     │   │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │   │
│  │  │  Task Analyzer  │───▶│ Route Decision  │───▶│  Model Selector │ │   │
│  │  │                 │    │                 │    │                 │ │   │
│  │  │ • Complexity    │    │ • Crew Type     │    │ • Strategy      │ │   │
│  │  │ • Keywords      │    │ • Strategy      │    │ • Model         │ │   │
│  │  │ • Context       │    │ • Priority      │    │ • Context Window│ │   │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘ │   │
│  │                                                                     │   │
│  │  Responsibilities:                                                  │   │
│  │  • Phân tích task complexity (0.0 - 1.0)                            │   │
│  │  • Detect crew type (PLANNING / CODING / CHAT)                      │   │
│  │  • Chọn routing strategy (FAST / DEEP / LOCAL)                      │   │
│  │  • Estimate cost & select model                                     │   │
│  └────────────────────────────────────┬────────────────────────────────┘   │
└───────────────────────────────────────┼────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │    PLANNING CREW    │  │    CODING CREW      │  │     CHAT CREW       │  │
│  │                     │  │                     │  │                     │  │
│  │  ┌───────────────┐  │  │  ┌───────────────┐  │  │  ┌───────────────┐  │  │
│  │  │ Task Planner  │  │  │  │ Code Generator│  │  │  │ Chat Agent    │  │  │
│  │  │   Agent       │  │  │  │    Agent      │  │  │  │               │  │  │
│  │  └───────────────┘  │  │  └───────────────┘  │  │  └───────────────┘  │  │
│  │  ┌───────────────┐  │  │                     │  │                     │  │
│  │  │   Architect   │  │  │                     │  │                     │  │
│  │  │    Agent      │  │  │                     │  │                     │  │
│  │  └───────────────┘  │  │                     │  │                     │  │
│  │                     │  │                     │  │                     │  │
│  │  Use case:          │  │  Use case:          │  │  Use case:          │  │
│  │  • Architecture     │  │  • Code generation  │  │  • Q&A              │  │
│  │  • System design    │  │  • Refactoring      │  │  • Explanation      │  │
│  │  • Task breakdown   │  │  • Debugging        │  │  • Simple chat      │  │
│  │  • Roadmap planning │  │  • Testing          │  │                     │  │
│  └──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘  │
└─────────────┼────────────────────────┼────────────────────────┼────────────┘
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         MEMORY LAYER                                 │   │
│  │                                                                     │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │   │
│  │  │  Short-term     │  │   Long-term     │  │   Working       │     │   │
│  │  │   (Redis)       │  │   (Qdrant)      │  │   (Markdown)    │     │   │
│  │  │                 │  │                 │  │                 │     │   │
│  │  │ • Session state │  │ • Vector search │  │ • Task plans    │     │   │
│  │  │ • Conversation  │  │ • Embeddings    │  │ • Code drafts   │     │   │
│  │  │   history       │  │ • Similarity    │  │ • Notes         │     │   │
│  │  │ • Cache         │  │   search        │  │                 │     │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘     │   │
│  │                                                                     │   │
│  │  Responsibilities:                                                  │   │
│  │  • Lưu trữ state của hệ thống                                       │   │
│  │  • Context sharing giữa các agents                                  │   │
│  │  • Long-term knowledge retrieval                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT LAYER                                    │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  Response       │  │  Streaming      │  │  Webhook        │             │
│  │  Formatter      │  │  Handler        │  │  Callback       │             │
│  │                 │  │                 │  │                 │             │
│  │ • JSON/XML      │  │ • SSE           │  │ • Async notify  │             │
│  │ • Markdown      │  │ • WebSocket     │  │ • Progress      │             │
│  │ • Structured    │  │ • Chunked       │  │   updates       │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
└───────────┼────────────────────┼────────────────────┼──────────────────────┘
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER RESPONSE                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. Gateway (Entry Point)

**File:** `src/orkit_crew/gateway/`

Gateway là **entry point duy nhất** của hệ thống. Mọi request từ user đều phải đi qua Gateway.

**Responsibilities:**
- Nhận request từ nhiều channels (HTTP API, WebSocket, CLI, Webhook)
- Authentication & Authorization (API keys, tokens)
- Request validation (schema, rate limiting)
- Error handling và response formatting
- Gửi kết quả về user

**Current State:**
- Hiện tại: `plano_client.py` chỉ là LLM client, không phải Gateway
- Cần refactor: Tạo Gateway server thực sự với HTTP API

**Future Gateway Structure:**
```
gateway/
├── __init__.py
├── server.py          # FastAPI/HTTP server
├── auth.py            # Authentication middleware
├── handlers/
│   ├── __init__.py
│   ├── http.py        # HTTP request handler
│   ├── websocket.py   # WebSocket handler
│   └── cli.py         # CLI handler (moved from root)
└── client.py          # LLM client (refactored from plano_client.py)
```

### 2. Council Router

**File:** `src/orkit_crew/core/router.py`

Router phân tích task và quyết định crew nào sẽ xử lý.

**Responsibilities:**
- **Task Analysis**: Phân tích complexity, keywords, context
- **Route Decision**: Chọn crew type (PLANNING/CODING/CHAT)
- **Strategy Selection**: Chọn strategy (FAST/DEEP/LOCAL)
- **Model Selection**: Chọn model phù hợp với task

**Key Classes:**
- `CouncilRouter`: Main router class
- `RouteDecision`: Data class chứa routing decision
- `CrewType`: Enum cho crew types
- `RoutingStrategy`: Enum cho strategies

### 3. Crews

**Files:** `src/orkit_crew/crews/`

Crews là nơi thực thi task với CrewAI agents.

**Base Class:** `BaseCrew`
- Quản lý agents và tasks
- Tích hợp với Memory
- Xử lý execution flow

**Specialized Crews:**

| Crew | Agents | Use Case |
|------|--------|----------|
| `PlanningCrew` | Task Planner, Architect | Architecture, system design, roadmap |
| `CodingCrew` | Code Generator | Code generation, refactoring, debugging |
| `ChatCrew` | Chat Agent | Q&A, explanation, simple chat |

### 4. Memory Layer

**File:** `src/orkit_crew/core/memory.py`

Multi-layer memory system:

| Layer | Technology | Use Case | TTL |
|-------|------------|----------|-----|
| Short-term | Redis | Session state, conversation history | 1-2 hours |
| Long-term | Qdrant | Vector search, embeddings | Permanent |
| Working | Markdown | Task plans, code drafts | Session |

**Key Classes:**
- `MemoryManager`: Unified interface
- `RedisMemory`: Short-term storage
- `QdrantMemory`: Vector storage
- `MarkdownMemory`: File-based storage

### 5. Output Layer

Format và gửi response về user:

- **Response Formatter**: JSON, Markdown, structured output
- **Streaming Handler**: SSE, WebSocket streaming
- **Webhook Callback**: Async notifications

## Data Flow

### 1. Request Flow (User → System)

```
User Request
    │
    ▼
┌─────────────────┐
│ Gateway Server  │ ◄── HTTP/WebSocket/CLI
│  - Validate     │
│  - Auth         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Council Router  │ ◄── Analyze task
│  - Complexity   │
│  - Crew type    │
│  - Strategy     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Selected Crew   │ ◄── Execute with CrewAI
│  - Agents       │
│  - Tasks        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Memory Layer    │ ◄── Store/retrieve context
│  - Redis        │
│  - Qdrant       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Output Layer    │ ◄── Format response
│  - Format       │
│  - Stream       │
└────────┬────────┘
         │
         ▼
    User Response
```

### 2. Example: Coding Task Flow

```
1. User: "Generate a FastAPI endpoint for user auth"
         │
         ▼
2. Gateway: Validate request, extract auth token
         │
         ▼
3. Router: Analyze task
   - Complexity: 0.6 (medium)
   - Keywords: "generate", "endpoint", "FastAPI"
   - Decision: CrewType.CODING, Strategy.FAST
         │
         ▼
4. CodingCrew: Execute
   - Code Generator Agent creates code
   - Memory: Store context in Redis
         │
         ▼
5. Output: Format as Markdown with code blocks
         │
         ▼
6. Gateway: Send HTTP response
```

### 3. Example: Planning Task Flow

```
1. User: "Design microservice architecture for e-commerce"
         │
         ▼
2. Gateway: Validate request
         │
         ▼
3. Router: Analyze task
   - Complexity: 0.85 (high)
   - Keywords: "design", "architecture", "microservice"
   - Decision: CrewType.PLANNING, Strategy.DEEP
         │
         ▼
4. PlanningCrew: Execute
   - Task Planner: Break down into subtasks
   - Architect: Design system components
   - Memory: Store in Qdrant for future retrieval
         │
         ▼
5. Output: Format as structured JSON + Markdown
         │
         ▼
6. Gateway: Send response with streaming
```

## Current vs Target Architecture

### Current (Problematic)

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│   CLI   │────▶│ Router  │────▶│  Crews  │────▶│ Planno  │
│ (Entry) │     │         │     │         │     │ Client  │
└─────────┘     └─────────┘     └─────────┘     │(Not a   │
                                                │Gateway) │
                                                └─────────┘
```

**Issues:**
1. CLI là entry point → Không thể nhận HTTP/WebSocket requests
2. `plano_client.py` chỉ là LLM client, không phải Gateway
3. Không có centralized request handling
4. Không có authentication layer

### Target (Fixed)

```
                    ┌─────────┐
                    │  User   │
                    └────┬────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    ▼                    ▼                    ▼
┌─────────┐        ┌─────────┐        ┌─────────┐
│ HTTP    │        │WebSocket│        │   CLI   │
│ Server  │        │ Server  │        │ Handler │
└────┬────┘        └────┬────┘        └────┬────┘
     │                  │                  │
     └──────────────────┼──────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │ Gateway Server  │ ◄── Entry Point
              │  - Auth         │
              │  - Validate     │
              │  - Rate Limit   │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Council Router  │
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │Planning │   │ Coding  │   │  Chat   │
   │  Crew   │   │  Crew   │   │  Crew   │
   └────┬────┘   └────┬────┘   └────┬────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
             ┌─────────────────┐
             │  Memory Layer   │
             │  - Redis        │
             │  - Qdrant       │
             │  - Markdown     │
             └─────────────────┘
```

## Migration Plan

### Phase 1: Refactor Gateway (Current Priority)

1. **Create Gateway Server**
   ```bash
   src/orkit_crew/gateway/
   ├── server.py      # FastAPI app
   ├── auth.py        # Auth middleware
   └── client.py      # Rename from plano_client.py
   ```

2. **Move CLI to Gateway**
   - `cli.py` → `gateway/handlers/cli.py`
   - CLI becomes một handler của Gateway

3. **Add HTTP API**
   ```python
   # POST /api/v1/tasks
   {
       "task": "Generate FastAPI endpoint",
       "context": {...},
       "options": {...}
   }
   ```

### Phase 2: Add WebSocket Support

- Real-time streaming responses
- Interactive chat mode

### Phase 3: Enhanced Router

- ML-based routing
- Feedback loop để improve routing decisions

## API Endpoints (Future)

```
POST   /api/v1/tasks              # Submit task
GET    /api/v1/tasks/{id}         # Get task status
POST   /api/v1/tasks/{id}/cancel  # Cancel task
GET    /api/v1/crews              # List available crews
POST   /api/v1/chat               # Interactive chat
WS     /ws/v1/stream              # WebSocket streaming
```

## Configuration

```python
# Gateway settings
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8080
GATEWAY_WORKERS=4

# Auth
API_KEY_HEADER=X-API-Key
JWT_SECRET=your-secret

# Rate limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# LLM Gateway (Planno)
PLANNO_URL=http://localhost:8787
PLANNO_API_KEY=your-key

# Memory
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
```

## Summary

Architecture đúng của Orkit Crew:

1. **Gateway** là entry point - nhận mọi request từ user
2. **Router** phân tích và route đến crew phù hợp
3. **Crews** thực thi task với CrewAI agents
4. **Memory** lưu trữ state và context
5. **Output** format và gửi response về user

Flow: `User → Gateway → Router → Crews → Memory → Output → User`

---

*Document version: 1.0*
*Last updated: 2026-03-06*
