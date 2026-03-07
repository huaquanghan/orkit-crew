# Orkit Crew — PRD-to-Product Pipeline Implementation Plan

> **Created:** 2026-03-07
> **Status:** APPROVED — Ready for implementation
> **Agent:** Claude Code should read this file and execute issues sequentially

---

## Executive Summary

Đơn giản hóa Orkit Crew thành **PRD-to-Product Pipeline**:
- **Input:** 1 PRD file (markdown + YAML frontmatter)
- **Process:** 3-phase pipeline (Analyze → Plan → Generate) với iterative human review
- **Output:** Next.js project files on disk
- **LLM:** GPT-5.4 via Planno Gateway
- **Stack MVP:** Next.js frontend only (TypeScript + Tailwind + shadcn/ui)

---

## Decisions Made

| Decision | Value |
|----------|-------|
| LLM | GPT-5.4 via Planno Gateway |
| Stack MVP | Next.js frontend only |
| Modes | Greenfield (new project) + Extend (add features) |
| PRD format | Markdown + YAML frontmatter |
| Scope control | User sets `scope: mvp` or `full` in frontmatter |
| Complexity | User hint or `auto` — agent assesses |
| Review mode | Step-by-step → Full markdown export → Iterative loop |
| State | Markdown-based (.orkit/ directory) — no Redis/Qdrant needed |
| Future | Web UI, RAG memory, more tech stacks |

---

## Architecture

```
PRD File (markdown + frontmatter)
         │
    ┌────▼─────────────┐
    │ Phase 1: Analyze  │ ←→ Human Review Loop
    │ (PRD Analyst)     │
    └────┬─────────────┘
         │ analysis.md
    ┌────▼─────────────┐
    │ Phase 2: Plan     │ ←→ Human Review Loop
    │ (Task Architect)  │
    └────┬─────────────┘
         │ plan.md
    ┌────▼─────────────┐
    │ Phase 3: Generate │ ←→ Human Review Loop
    │ (Code Generator)  │
    └────┬─────────────┘
         │
    Project Files on Disk
```

### What We Keep vs Cut from Current Codebase

| Keep (refactor) | Cut/Ignore |
|-----------------|-----------|
| `BaseCrew` pattern | `Council Router` → fixed pipeline |
| `PlanningCrew` → PRD Analyst + Task Architect | `ChatCrew` concept |
| `CodingCrew` → Code Generator | `Gateway HTTP server` |
| `plano_client.py` | `Qdrant memory` |
| `config.py` (Pydantic settings) | `Redis memory` |
| `MarkdownMemory` → Session state | `State machine` → session.json |
| CLI (typer) | Unused `tools/` module |
| Docker Compose (simplified) | Duplicate dirs outside `orkit_crew/` |

### Target Directory Structure

```
src/orkit_crew/
├── __init__.py
├── main.py
├── cli.py                    # Pipeline CLI commands
├── core/
│   ├── __init__.py
│   ├── config.py             # Pydantic settings (simplified)
│   ├── prd_parser.py         # PRD + frontmatter parser
│   └── session.py            # Session manager
├── agents/                   # RENAMED from crews/
│   ├── __init__.py
│   ├── base.py               # Base agent/crew class
│   ├── analyst.py            # PRD Analyst (Phase 1)
│   ├── architect.py          # Task Architect (Phase 2)
│   └── generator.py          # Code Generator (Phase 3)
├── pipeline/
│   ├── __init__.py
│   └── orchestrator.py       # Pipeline orchestration logic
├── gateway/
│   ├── __init__.py
│   └── llm_client.py         # RENAMED from plano_client.py
└── templates/
    └── prd_template.md       # PRD template file
```

---

## Implementation Tracker

| # | Issue | Depends On | Week |
|---|-------|------------|------|
| 0 | [META] PRD-to-Product Pipeline Tracker | — | — |
| 1 | [SETUP] Cleanup Codebase & Restructure | — | 1 |
| 2 | [CORE] PRD Template + Frontmatter Parser | #1 | 1 |
| 3 | [CORE] Session Manager (Markdown State) | #1 | 1 |
| 4 | [AGENT] Phase 1 — PRD Analyst | #2, #3 | 2 |
| 5 | [AGENT] Phase 2 — Task Architect | #4 | 2 |
| 6 | [AGENT] Phase 3 — Code Generator (Next.js) | #5 | 3 |
| 7 | [CLI] Pipeline Orchestrator + Commands | #4, #5, #6 | 3 |
| 8 | [CONFIG] Stack Config + Planno Client Cleanup | #1 | 1 |
| 9 | [TEST] Test Suite + Sample PRDs | #7 | 4 |

### Execution Order

```
Issue 1 (Setup)
    ├──→ Issue 2 (PRD Parser)     ─┐
    ├──→ Issue 3 (Session Manager) ─┼──→ Issue 4 (Analyst Agent)
    └──→ Issue 8 (Config)         ─┘        │
                                         Issue 5 (Architect Agent)
                                             │
                                         Issue 6 (Code Gen Agent)
                                             │
                                         Issue 7 (CLI Orchestrator)
                                             │
                                         Issue 9 (Tests)
```

---

## ISSUE 0: [META] PRD-to-Product Pipeline — Brainstorm & Implementation Tracker

**Labels:** `meta`, `tracking`

This is the meta issue. It tracks all other issues and contains the brainstorm context. Create this issue with the content of the "Executive Summary", "Decisions Made", "Architecture", and "Implementation Tracker" sections above.

After creating all issues, update this meta issue body to include the actual GitHub issue numbers with links.

---

## ISSUE 1: [SETUP] Cleanup Codebase & Restructure for PRD Pipeline

**Labels:** `setup`, `refactor`, `priority:critical`
**Depends on:** Nothing (first issue)
**Blocks:** #2, #3, #8

### Goal

Dọn dẹp codebase hiện tại, cắt bỏ components không cần, restructure cho PRD-to-Product pipeline.

### Task 1: Delete unnecessary files/directories

```
DELETE these:
src/core/                    # duplicate of src/orkit_crew/core/
src/crews/                   # duplicate of src/orkit_crew/crews/
src/gateway/                 # duplicate of src/orkit_crew/gateway/
src/__init__.py              # wrong level
src/__pycache__/             # should be gitignored
src/orkit_crew/__pycache__/  # should be gitignored
src/orkit_crew/tools/        # empty, unused
src/orkit_crew/core/router.py   # replaced by fixed pipeline
src/orkit_crew/core/state.py    # replaced by session.json
```

### Task 2: Add proper .gitignore

Create/update `.gitignore`:

```
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
venv/
ENV/
.vscode/
.idea/
*.swp
*.swo
.env
.env.local
.pytest_cache/
htmlcov/
.coverage
.DS_Store
Thumbs.db
```

### Task 3: Restructure src/orkit_crew/

Rename `crews/` → `agents/` directory. Create new directories:

```
mkdir -p src/orkit_crew/agents
mkdir -p src/orkit_crew/pipeline
mkdir -p src/orkit_crew/templates
```

Move files:
- `src/orkit_crew/crews/base.py` → `src/orkit_crew/agents/base.py`
- `src/orkit_crew/crews/planning_crew.py` → DELETE (will be replaced by analyst.py + architect.py)
- `src/orkit_crew/crews/coding_crew.py` → DELETE (will be replaced by generator.py)
- `src/orkit_crew/gateway/plano_client.py` → `src/orkit_crew/gateway/llm_client.py`

Create empty placeholder files:
- `src/orkit_crew/core/__init__.py`
- `src/orkit_crew/agents/__init__.py`
- `src/orkit_crew/pipeline/__init__.py`
- `src/orkit_crew/gateway/__init__.py`
- `src/orkit_crew/core/prd_parser.py` (empty, placeholder)
- `src/orkit_crew/core/session.py` (empty, placeholder)
- `src/orkit_crew/agents/analyst.py` (empty, placeholder)
- `src/orkit_crew/agents/architect.py` (empty, placeholder)
- `src/orkit_crew/agents/generator.py` (empty, placeholder)
- `src/orkit_crew/pipeline/orchestrator.py` (empty, placeholder)

### Task 4: Update config.py

Replace `src/orkit_crew/core/config.py` with simplified version — remove Redis/Qdrant, add pipeline config:

```python
"""Orkit Crew Configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Planno LLM Gateway
    planno_url: str = "http://localhost:8787"
    planno_api_key: str = ""

    # Default model
    default_model: str = "gpt-5.4"

    # Application
    app_env: str = "development"
    log_level: str = "INFO"

    # Pipeline defaults
    default_framework: str = "nextjs"
    default_language: str = "typescript"
    default_styling: str = "tailwindcss"
    default_ui_library: str = "shadcn"
    default_package_manager: str = "pnpm"
    default_nextjs_router: str = "app"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

### Task 5: Update .env.example

```
# Planno LLM Gateway
PLANNO_URL=http://localhost:8787
PLANNO_API_KEY=your-api-key-here

# Default Model
DEFAULT_MODEL=gpt-5.4

# Application
APP_ENV=development
LOG_LEVEL=INFO

# Pipeline Defaults (override in PRD frontmatter)
DEFAULT_FRAMEWORK=nextjs
DEFAULT_LANGUAGE=typescript
DEFAULT_STYLING=tailwindcss
DEFAULT_UI_LIBRARY=shadcn
DEFAULT_PACKAGE_MANAGER=pnpm
```

### Task 6: Update pyproject.toml

```toml
[project]
name = "orkit-crew"
version = "0.2.0"
description = "PRD-to-Product AI Pipeline — Generate Next.js projects from PRD documents"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}

dependencies = [
    "crewai>=0.95.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
    "typer>=0.12.0",
    "pyyaml>=6.0.0",
    "python-frontmatter>=1.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "black>=24.0.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
]

[project.scripts]
orkit = "orkit_crew.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/orkit_crew"]

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["src"]
```

REMOVED dependencies: click, redis, qdrant-client
ADDED dependencies: pyyaml, python-frontmatter

### Task 7: Simplify docker-compose.yml

```yaml
version: "3.8"

services:
  app:
    build: .
    container_name: orkit-app
    environment:
      - PLANNO_URL=${PLANNO_URL:-http://host.docker.internal:8787}
      - PLANNO_API_KEY=${PLANNO_API_KEY}
      - DEFAULT_MODEL=${DEFAULT_MODEL:-gpt-5.4}
      - APP_ENV=${APP_ENV:-development}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./src:/app/src
      - ./.env:/app/.env
      - ./workspace:/app/workspace
    command: ["orkit", "--help"]
    stdin_open: true
    tty: true
```

REMOVED: redis and qdrant services

### Task 8: Clean up files committed by mistake

Delete the `issues/` directory that was accidentally created:
```
DELETE: issues/1.md
DELETE: issues/2026-03-07-PRD-to-Product-Pipeline.md
```

### Acceptance Criteria

- [ ] All deleted files/dirs are gone
- [ ] `.gitignore` properly configured
- [ ] New directory structure matches target
- [ ] `config.py` simplified — no Redis/Qdrant references
- [ ] `.env.example` updated
- [ ] `pyproject.toml` has correct dependencies
- [ ] `docker-compose.yml` simplified
- [ ] Placeholder files exist for new modules
- [ ] `pip install -e .` works
- [ ] `python -c "import orkit_crew"` works without errors
- [ ] `issues/` directory deleted

---

## ISSUE 2: [CORE] PRD Template + Frontmatter Parser

**Labels:** `core`, `feature`, `priority:critical`
**Depends on:** #1
**Blocks:** #4

### Goal

Tạo PRD template chuẩn với YAML frontmatter và build parser để extract metadata + content sections.

### Task 1: Create PRD Template

**File: `src/orkit_crew/templates/prd_template.md`**

```markdown
---
# === ORKIT PRD METADATA ===
project_name: "my-project"
version: "1.0"

# Mode: greenfield | extend
mode: greenfield

# Scope: mvp (P0 features only) | full (all features)
scope: mvp

# Tech Stack
stack:
  framework: nextjs
  language: typescript
  styling: tailwindcss
  ui_library: shadcn
  package_manager: pnpm

# Next.js Config
nextjs:
  router: app
  src_dir: true

# Complexity: auto | low | medium | high
complexity: auto

# Output
output_dir: ./output

# Extend mode only
# existing_dir: ./my-existing-project

# Extra instructions
notes: |
  - Server Components preferred
  - Mobile-first responsive
---

# [Project Name]

## 1. Tổng quan
[Mô tả sản phẩm 2-3 câu]

## 2. Mục tiêu
- [ ] Goal 1
- [ ] Goal 2

## 3. Target Users
[Persona chính]

## 4. Core Features

### Feature 1: [Tên]
- **Priority:** P0
- **Mô tả:** [Chi tiết]
- **User story:** As a [user], I want to [action] so that [benefit]
- **UI Components:**
  - [ ] Component A
  - [ ] Component B
- **Acceptance criteria:**
  - [ ] Criteria 1
  - [ ] Criteria 2

### Feature 2: [Tên]
- **Priority:** P1
- **Mô tả:** [Chi tiết]
- **User story:** As a [user], I want to [action] so that [benefit]
- **UI Components:**
  - [ ] Component A
- **Acceptance criteria:**
  - [ ] Criteria 1

## 5. Pages / Routes
| Route | Page | Description |
|-------|------|-------------|
| `/` | Home | Landing page |
| `/about` | About | About page |

## 6. UI/UX Requirements
- **Design style:** [Modern/Minimal/etc.]
- **Responsive:** Mobile-first
- **Dark mode:** Yes / No

## 7. Non-functional Requirements
- **Performance:** [e.g., LCP < 2.5s]
- **SEO:** [Requirements]

## 8. Out of Scope
- [What NOT to build]
```

### Task 2: Create Pydantic models and parser

**File: `src/orkit_crew/core/prd_parser.py`**

Build these classes:

**Enums:**
- `ProjectMode` (greenfield, extend)
- `ProjectScope` (mvp, full)
- `Complexity` (auto, low, medium, high)
- `FeaturePriority` (P0, P1, P2)

**Models:**
- `StackConfig` — framework, language, styling, ui_library, package_manager
- `NextjsConfig` — router, src_dir
- `Feature` — name, priority, description, user_story, ui_components (list), acceptance_criteria (list), raw_markdown
- `PageRoute` — route, page_name, description
- `PRDMetadata` — all frontmatter fields mapped to models above
- `PRDContent` — overview, goals (list), target_users, features (list[Feature]), pages (list[PageRoute]), ui_requirements, non_functional, out_of_scope, raw_body
- `PRDDocument` — metadata (PRDMetadata) + content (PRDContent) + source_path
  - Method: `get_mvp_features()` → returns only P0 features
  - Method: `get_all_features()` → returns all sorted by priority
  - Method: `get_features_for_scope()` → returns features based on scope setting

**Parser class: `PRDParser`**
- `parse_file(file_path)` → reads file, calls parse_string
- `parse_string(content, source_path)` → uses `python-frontmatter` library to split frontmatter from body
- `_parse_metadata(meta_dict)` → maps YAML dict to PRDMetadata
- `_parse_body(body_str)` → splits by `## ` headings, extracts each section
- `_split_sections(body)` → regex split by `## N. Section Name`
- `_extract_features(text)` → splits by `### `, extracts Feature fields
- `_extract_priority(text)` → regex for `**Priority:** P0`
- `_extract_field(text, field_name)` → regex for `**FieldName:** value`
- `_extract_checklist(text)` → regex for `- [ ] item` or `- [x] item`
- `_extract_pages(text)` → parse markdown table format

**Validation function: `validate_prd(doc)`**
Returns list of warning strings:
- project_name not set
- overview empty
- no features found
- scope=mvp but no P0 features
- mode=extend but no existing_dir
- no pages defined

**Convenience function: `parse_prd(file_path)`**
Wrapper that creates PRDParser and calls parse_file.

### Task 3: Support both Vietnamese and English section headers

The parser `_split_sections` should handle:
- `## 1. Tổng quan` AND `## 1. Overview`
- `## 2. Mục tiêu` AND `## 2. Goals`
- `## 4. Core Features` (English only is fine for features)

Use a mapping dict for section name normalization.

### Acceptance Criteria

- [ ] PRD template file exists at `src/orkit_crew/templates/prd_template.md`
- [ ] `PRDParser().parse_file("path.md")` returns `PRDDocument`
- [ ] Frontmatter correctly parsed into `PRDMetadata`
- [ ] Nested `stack` and `nextjs` configs parse correctly
- [ ] Features extracted with priority, description, user_story, components, criteria
- [ ] `get_mvp_features()` returns only P0
- [ ] `get_features_for_scope()` respects scope setting
- [ ] Page routes extracted from table format
- [ ] `validate_prd()` returns meaningful warnings
- [ ] Parser handles both Vietnamese and English headers
- [ ] Parser does not crash on minimal/malformed PRD files

---

## ISSUE 3: [CORE] Session Manager — Markdown-based State

**Labels:** `core`, `feature`, `priority:critical`
**Depends on:** #1
**Blocks:** #4, #7

### Goal

Build session manager that tracks pipeline state using filesystem (JSON + Markdown). No database needed. Future Web UI compatible.

### Session Directory Structure

```
.orkit/
├── session.json              # Session metadata & current state
├── analysis.md               # Phase 1 output
├── plan.md                   # Phase 2 output
├── generation_log.md         # Phase 3 progress
├── reviews/                  # Version history
│   ├── analysis_v1.md
│   ├── analysis_v2.md
│   ├── plan_v1.md
│   └── plan_v2.md
└── context/
    ├── conversation.jsonl    # Conversation log (append-only)
    └── decisions.md          # Key decisions from reviews
```

### File: `src/orkit_crew/core/session.py`

**Enums:**
- `PipelinePhase` — init, analyzing, analysis_review, planning, plan_review, generating, generation_review, completed, failed
- `PhaseStatus` — pending, in_progress, awaiting_review, approved, revision_requested, failed

**Models:**
- `PhaseState` — status, version (int), started_at, completed_at, error
- `SessionData` — session_id, prd_file, project_name, output_dir, current_phase, created_at, updated_at, analysis (PhaseState), planning (PhaseState), generation (PhaseState), total_revisions (int), generated_files (list[str])

**SessionManager class:**

Constructor: `__init__(self, base_dir)` — sets up paths for .orkit/ directory

Lifecycle methods:
- `init_session(session_id, prd_file, project_name, output_dir)` → creates .orkit/ dirs, initializes session.json
- `load_session()` → reads session.json from disk
- `has_session()` → checks if session.json exists
- `session` property → returns current SessionData (raises if not loaded)

Phase transition methods:
- `start_phase(phase)` → updates current_phase + phase state to in_progress
- `complete_phase(phase)` → marks phase as awaiting_review
- `approve_phase(phase)` → marks phase as approved, advances to next phase
- `request_revision(phase, feedback)` → increments version, marks as revision_requested
- `fail_phase(phase, error)` → marks as failed

File management methods:
- `save_analysis(content)` → writes analysis.md, saves version to reviews/
- `save_plan(content)` → writes plan.md, saves version to reviews/
- `save_generation_log(content)` → writes generation_log.md
- `get_analysis()` → reads analysis.md
- `get_plan()` → reads plan.md
- `add_generated_file(file_path)` → appends to generated_files list

Context methods:
- `log_conversation(role, content)` → appends to conversation.jsonl
- `log_decision(decision)` → appends to decisions.md

Internal:
- `_save()` → writes session.json to disk (updates updated_at timestamp)
- `_get_phase_state(phase)` → returns the PhaseState for a given PipelinePhase
- `_version_file(source, phase_name, version)` → copies file to reviews/ with version suffix

### Acceptance Criteria

- [ ] `SessionManager(base_dir).init_session(...)` creates `.orkit/` directory structure
- [ ] `session.json` contains all fields, is valid JSON
- [ ] Phase transitions work: init → analyzing → analysis_review → planning → etc.
- [ ] `save_analysis(content)` writes `.orkit/analysis.md`
- [ ] Version tracking: each save creates `reviews/analysis_v1.md`, `v2`, etc.
- [ ] `request_revision()` increments version counter
- [ ] `log_conversation()` appends JSONL (one JSON object per line)
- [ ] `load_session()` correctly restores state from disk
- [ ] `has_session()` returns True/False correctly
- [ ] Session survives process restart (can resume)

---

## ISSUE 4: [AGENT] Phase 1 — PRD Analyst Agent

**Labels:** `agent`, `feature`, `priority:high`
**Depends on:** #2, #3
**Blocks:** #5

### Goal

Build PRD Analyst agent that reads a PRD, extracts key information, identifies ambiguities, and conducts interactive Q&A with the user.

### File: `src/orkit_crew/agents/analyst.py`

**Class: `PRDAnalystAgent`**

This agent uses CrewAI. It should extend or use the `BaseCrew` pattern from `agents/base.py`.

**Agent Configuration:**
```python
role = "PRD Analyst"
goal = "Analyze the PRD document thoroughly, extract all requirements, identify ambiguities and missing information, and produce a comprehensive analysis report"ackstory = """You are a senior product analyst with 10+ years of experience breaking down 
Product Requirement Documents into actionable technical specifications. You excel at 
identifying gaps, ambiguities, and implicit requirements that others miss. You always 
ask clarifying questions before making assumptions."""
```

**Input:**
- `PRDDocument` (parsed PRD from prd_parser)

**Output:** `analysis.md` with this structure:
```markdown
# PRD Analysis: {project_name}

## Summary
[2-3 sentence summary of the product]

## Key Features Extracted
| # | Feature | Priority | Complexity | Notes |
|---|---------|----------|------------|-------|
| 1 | ... | P0 | Medium | ... |

## Technical Requirements
- Framework: {from frontmatter}
- Key libraries needed: [inferred from features]
- Data flow: [description]

## Ambiguities & Questions
1. **[Question]** — Why it matters: [impact]
2. **[Question]** — Why it matters: [impact]

## Assumptions Made
1. [Assumption] — Based on: [reasoning]

## Complexity Assessment
- **Overall:** {low/medium/high}
- **Estimated components:** {number}
- **Estimated pages:** {number}
- **Generation strategy:** {full/scaffold/hybrid}

## Risk Factors
- [Risk 1]
- [Risk 2]
```

**Interactive Q&A Flow:**
1. Agent generates initial analysis with questions
2. Questions are presented to user one-by-one via CLI
3. User answers each question
4. Agent revises analysis incorporating answers
5. Full analysis shown to user for approval
6. If user requests revision → loop back to step 4

**Method: `async analyze(prd_doc, session_manager) -> str`**
- Creates CrewAI agent with above config
- Creates task: "Analyze this PRD and produce analysis report"
- Passes full PRD content as context
- Returns analysis markdown string

**Method: `extract_questions(analysis_text) -> list[str]`**
- Parses the "Ambiguities & Questions" section
- Returns list of question strings for interactive Q&A

**Method: `async revise_analysis(original_analysis, qa_pairs, prd_doc) -> str`**
- Takes original analysis + user answers
- Produces revised analysis with answers incorporated
- Removes answered questions, updates assumptions

### Acceptance Criteria

- [ ] Agent produces well-structured `analysis.md`
- [ ] Questions are extracted and presentable to user
- [ ] Revision incorporates user answers correctly
- [ ] Analysis includes complexity assessment
- [ ] Works with minimal PRD (just overview + 1 feature)
- [ ] Works with detailed PRD (5+ features, all sections filled)
- [ ] Session manager tracks analysis versions

---

## ISSUE 5: [AGENT] Phase 2 — Task Architect Agent

**Labels:** `agent`, `feature`, `priority:high`
**Depends on:** #4
**Blocks:** #6

### Goal

Build Task Architect agent that takes PRD + approved analysis and produces a detailed task breakdown plan.

### File: `src/orkit_crew/agents/architect.py`

**Class: `TaskArchitectAgent`**

**Agent Configuration:**
```python
role = "Task Architect"
goal = "Break down the analyzed PRD into a detailed, ordered task plan with specific file paths, component names, and implementation details for a Next.js project"
backstory = """You are a senior frontend architect specializing in Next.js and React. 
You excel at breaking complex requirements into small, implementable tasks. You always 
think about component hierarchy, data flow, file organization, and reusability. 
You follow Next.js App Router best practices."""
```

**Input:**
- `PRDDocument` (parsed PRD)
- `analysis.md` content (approved analysis from Phase 1)

**Output:** `plan.md` with this structure:
```markdown
# Implementation Plan: {project_name}

## Tech Stack
- Framework: Next.js (App Router)
- Language: TypeScript
- Styling: Tailwind CSS
- UI Library: shadcn/ui
- Package Manager: pnpm

## Project Structure
```
{project_name}/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   └── {route}/
│   │       └── page.tsx
│   ├── components/
│   │   ├── ui/            # shadcn components
│   │   └── {feature}/     # feature components
│   └── lib/
│       └── utils.ts
├── public/
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── next.config.mjs
```

## Tasks

### Task 1: Project Setup
- **Type:** setup
- **Files to create:**
  - `package.json`
  - `tsconfig.json`
  - `tailwind.config.ts`
  - `next.config.mjs`
  - `src/app/layout.tsx`
  - `src/app/globals.css`
  - `src/lib/utils.ts`
- **Description:** Initialize Next.js project with TypeScript, Tailwind, shadcn/ui
- **Dependencies:** none
- **Complexity:** low

### Task 2: {Feature Name}
- **Type:** feature
- **Files to create:**
  - `src/app/{route}/page.tsx`
  - `src/components/{feature}/{Component}.tsx`
- **Description:** [What to implement]
- **Dependencies:** Task 1
- **Complexity:** {low/medium/high}
- **Acceptance criteria:**
  - [ ] ...

[... more tasks ...]

## Dependency Graph
```
Task 1 (Setup)
├── Task 2 (Feature A)
│   └── Task 4 (Feature A detail)
├── Task 3 (Feature B)
└── Task 5 (Shared components)
```

## Summary
- **Total tasks:** {N}
- **Total files:** {N}
- **Estimated complexity:** {low/medium/high}
```

**Step-by-step Review Flow:**
1. Agent generates full plan
2. Each task is presented to user one-by-one:
   ```
   📋 Task 1/N: {title}
      Type: {setup/feature}
      Files: {list}
      Complexity: {low/medium/high}
      [approve/edit/skip/insert]:
   ```
3. User can:
   - `approve` — accept task as-is
   - `edit` — provide feedback, agent revises that task
   - `skip` — remove task from plan
   - `insert` — add a new task before this one
4. After all tasks reviewed → show full plan.md
5. User approves or requests full revision

**Method: `async plan(prd_doc, analysis_content, session_manager) -> str`**
- Creates CrewAI agent
- Generates task plan
- Returns plan markdown

**Method: `parse_tasks(plan_content) -> list[dict]`**
- Parses plan.md to extract individual tasks as dicts
- Each dict: {title, type, files, description, dependencies, complexity, acceptance_criteria}

**Method: `async revise_task(task_dict, feedback, full_plan) -> str`**
- Revises a single task based on user feedback
- Returns updated plan with that task modified

**Method: `async revise_plan(plan_content, feedback) -> str`**
- Full plan revision based on general feedback

### Acceptance Criteria

- [ ] Agent produces well-structured `plan.md`
- [ ] Tasks have specific file paths (not generic)
- [ ] File paths follow Next.js App Router conventions
- [ ] Project structure is valid Next.js + TypeScript + Tailwind + shadcn
- [ ] Tasks are properly ordered with dependencies
- [ ] `parse_tasks()` correctly extracts task list
- [ ] Single task revision works
- [ ] Full plan revision works
- [ ] Handles MVP scope (fewer tasks) vs full scope correctly

---

## ISSUE 6: [AGENT] Phase 3 — Code Generator Agent (Next.js)

**Labels:** `agent`, `feature`, `priority:high`
**Depends on:** #5
**Blocks:** #7

### Goal

Build Code Generator agent that takes the approved plan and generates actual Next.js project files on disk.

### File: `src/orkit_crew/agents/generator.py`

**Class: `CodeGeneratorAgent`**

**Agent Configuration:**
```python
role = "Senior Next.js Developer"
goal = "Generate production-quality Next.js code based on the implementation plan. Write clean, typed TypeScript with proper component structure, Tailwind styling, and shadcn/ui components."
backstory = """You are a senior frontend developer with deep expertise in Next.js App Router, 
React Server Components, TypeScript, and Tailwind CSS. You write clean, maintainable code 
following best practices. You use shadcn/ui components and always ensure responsive design. 
You add helpful comments only where logic is complex."""
```

**Input:**
- `PRDDocument` (parsed PRD)
- `analysis.md` content
- `plan.md` content (approved plan from Phase 2)
- Output directory path

**Process — Task by Task:**
1. Parse tasks from plan.md
2. For each task:
   a. Generate code for all files in that task
   b. Write files to disk in output directory
   c. Show user summary of generated files
   d. User can review and request revision
3. After all tasks complete → show summary

**File Writing:**
- Create directories as needed (`os.makedirs`)
- Write files with proper encoding (utf-8)
- For Next.js setup task: generate proper `package.json`, `tsconfig.json`, etc.
- Track all generated files in session

**Method: `async generate(prd_doc, analysis, plan, output_dir, session_manager) -> list[str]`**
- Main method — generates all files task by task
- Returns list of generated file paths

**Method: `async generate_task(task_dict, context, output_dir) -> list[str]`**
- Generates files for a single task
- Context includes PRD + analysis + plan + previously generated files
- Returns list of file paths created

**Method: `async revise_file(file_path, feedback, context) -> str`**
- Revises a specific generated file based on feedback
- Reads current content, applies feedback, writes back
- Returns new file content

**Method: `write_file(output_dir, relative_path, content) -> str`**
- Writes a file to disk
- Creates parent directories if needed
- Returns absolute path

**Next.js Specific Knowledge — hardcode these patterns:**

For `scope: mvp` or `scope: full` greenfield projects, Task 1 (Setup) should always generate:
```
{project}/
├── package.json          # next, react, typescript, tailwind, shadcn deps
├── tsconfig.json         # standard Next.js TS config
├── tailwind.config.ts    # with shadcn/ui theme
├── next.config.mjs       # standard config
├── postcss.config.mjs    # tailwind postcss
├── components.json       # shadcn/ui config
├── src/
│   ├── app/
│   │   ├── layout.tsx    # Root layout with fonts, metadata
│   │   ├── page.tsx      # Home page
│   │   └── globals.css   # Tailwind directives + shadcn vars
│   └── lib/
│       └── utils.ts      # cn() helper for shadcn
└── public/
    └── (empty)
```

**Iterative Revision Flow:**
After each task is generated:
```
📦 Task 2/6: Auth Pages ✅
   Created: src/app/login/page.tsx
            src/app/register/page.tsx
            src/components/auth/LoginForm.tsx
            src/components/auth/RegisterForm.tsx

   [next/review/revise]:
   > revise
   Feedback: > LoginForm cần thêm social login buttons
   🔄 Revising src/components/auth/LoginForm.tsx...
   Updated ✅
```

### Acceptance Criteria

- [ ] Generates valid Next.js project structure
- [ ] TypeScript files have proper types (no `any`)
- [ ] Tailwind classes used for styling
- [ ] shadcn/ui components imported correctly
- [ ] `package.json` has correct dependencies
- [ ] App Router conventions followed (layout.tsx, page.tsx, loading.tsx)
- [ ] Server Components used by default, 'use client' only when needed
- [ ] Generated code is formatted and readable
- [ ] Single file revision works
- [ ] All generated files tracked in session
- [ ] Handles both greenfield and extend mode

---

## ISSUE 7: [CLI] Pipeline Orchestrator + Commands

**Labels:** `cli`, `feature`, `priority:high`
**Depends on:** #4, #5, #6
**Blocks:** #9

### Goal

Build the CLI commands and pipeline orchestrator that ties all phases together with Rich console UI.

### File: `src/orkit_crew/pipeline/orchestrator.py`

**Class: `PipelineOrchestrator`**

This is the main controller. It coordinates:
- PRD parsing
- Session management
- Agent execution (Phase 1, 2, 3)
- Human review loops
- State persistence

**Constructor:** `__init__(self, prd_path, output_dir=None)`
- Parses PRD file
- Determines output_dir (from frontmatter or CLI arg)
- Initializes SessionManager

**Method: `async run()`**
- Main pipeline execution
- Checks for existing session (resume support)
- Runs phases sequentially with review loops

**Method: `async run_analysis()`**
- Runs Phase 1: PRD Analyst
- Interactive Q&A loop
- Review loop until approved

**Method: `async run_planning()`**
- Runs Phase 2: Task Architect
- Step-by-step task review
- Review loop until approved

**Method: `async run_generation()`**
- Runs Phase 3: Code Generator
- Task-by-task generation with review
- Revision loop per task

**Method: `async review_loop(phase, content) -> tuple[bool, str]`**
- Generic review loop
- Shows content → asks approve/edit/redo
- Returns (approved: bool, final_content: str)

### File: `src/orkit_crew/cli.py`

Replace current CLI with new commands using Typer:

```python
import typer
from rich.console import Console

app = typer.Typer(name="orkit", help="PRD-to-Product AI Pipeline")
console = Console()

@app.command()
def prd(
    prd_file: str = typer.Argument(..., help="Path to PRD markdown file"),
    output: str = typer.Option(None, "--output", "-o", help="Output directory"),
):
    """Start PRD-to-Product pipeline from a PRD file."""
    # 1. Parse PRD
    # 2. Validate PRD (show warnings)
    # 3. Show summary + confirm
    # 4. Init session
    # 5. Run pipeline (orchestrator.run())

@app.command()
def resume(
    directory: str = typer.Argument(".", help="Directory with .orkit/ session"),
):
    """Resume an existing pipeline session."""
    # 1. Load session
    # 2. Determine current phase
    # 3. Resume from that phase

@app.command()
def status(
    directory: str = typer.Argument(".", help="Directory with .orkit/ session"),
):
    """Show current pipeline status."""
    # 1. Load session
    # 2. Display status table with Rich

@app.command()
def template(
    output: str = typer.Option("./prd.md", "--output", "-o"),
):
    """Generate a blank PRD template file."""
    # 1. Copy template to output path
    # 2. Print success message

def main():
    app()
```

**Rich Console UI Elements:**

Use Rich library for beautiful terminal output:
- `Console().print()` with markup for colors
- `Panel` for section headers
- `Table` for task listings
- `Prompt.ask()` for user input
- `Progress` for generation progress
- `Syntax` for showing generated code

**Example UI flow for `orkit prd ./my-prd.md`:**
```
🚀 Orkit Crew — PRD-to-Product Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 PRD: ./my-prd.md
📁 Output: ./my-app/
🔧 Stack: Next.js + TypeScript + Tailwind + shadcn/ui
📐 Mode: greenfield | Scope: mvp

Continue? [Y/n]: 

━━━ PHASE 1: PRD Analysis ━━━━━━━━━━━━━

🔍 Analyzing PRD...

[analysis output]

❓ Questions:
  Q1: [question]
  > [user types answer]
  
  Q2: [question]
  > [user types answer]

📝 Analysis saved → .orkit/analysis.md
Approve? [approve/edit/redo]: approve ✅

━━━ PHASE 2: Task Planning ━━━━━━━━━━━━

🏗️ Planning tasks...

📋 Task 1/N: [title]
   Files: [list]
   [approve/edit/skip/insert]: approve ✅

📋 Task 2/N: [title]
   ...

📝 Plan saved → .orkit/plan.md
Approve full plan? [approve/edit/redo]: approve ✅

━━━ PHASE 3: Code Generation ━━━━━━━━━━

⚡ Generating...

📦 Task 1/N: [title] ✅
   Created: [file list]
   [next/review/revise]: next

📦 Task 2/N: [title] ✅
   ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DONE! Project generated at ./my-app/
   {N} files created
💾 Session saved. Run `orkit resume` to continue.
```

### Acceptance Criteria

- [ ] `orkit prd ./prd.md` starts full pipeline
- [ ] `orkit prd ./prd.md --output ./dir` respects output flag
- [ ] `orkit resume` loads and continues existing session
- [ ] `orkit status` shows current pipeline state
- [ ] `orkit template` generates blank PRD template
- [ ] All three phases run sequentially with review loops
- [ ] User can approve/edit/redo at each phase
- [ ] Rich console output is readable and well-formatted
- [ ] Pipeline state persists — can Ctrl+C and resume later
- [ ] Error handling: graceful messages on LLM failure, invalid PRD, etc.

---

## ISSUE 8: [CONFIG] Stack Config + Planno Client Cleanup

**Labels:** `config`, `refactor`, `priority:high`
**Depends on:** #1
**Blocks:** #4

### Goal

Clean up Planno LLM client, ensure it works reliably with GPT-5.4, and add stack configuration support.

### Task 1: Rename and cleanup LLM client

**File: `src/orkit_crew/gateway/llm_client.py`** (renamed from plano_client.py)

Keep the existing httpx async client but:
- Rename class to `LLMClient` (from `PlannoClient`)
- Add proper error handling with retries
- Add timeout configuration
- Add logging
- Ensure streaming support works

```python
"""LLM Client — Async client for Planno Gateway."

import logging
from typing import Any, AsyncIterator, Optional

import httpx
from pydantic import BaseModel

from orkit_crew.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Structured LLM response."""
    content: str
    model: str
    usage: dict[str, int] = {}


class LLMClient:
    """Async LLM client for Planno Gateway."""

    def __init__(self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        settings = get_settings()
        self.base_url = base_url or settings.planno_url
        self.api_key = api_key or settings.planno_api_key
        self.model = model or settings.default_model
        self.timeout = timeout
        self.max_retries = max_retries

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send chat completion request."""
        # Implementation with retry logic and error handling
        ...

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream chat completion response."""
        ...

    async def health_check(self) -> bool:
        """Check if LLM gateway is reachable."""
        ...
```

Add proper error handling:
- Connection timeout → retry with backoff
- 429 rate limit → wait and retry
- 500+ server error → retry
- Auth error → clear error message
- Log all requests/responses at DEBUG level

### Task 2: Stack configuration defaults

The stack config comes from PRD frontmatter (parsed in Issue #2). This issue ensures the `config.py` defaults align with the frontmatter schema.

No additional code needed beyond what's in Issue #1 Task 4, but verify that:
- `Settings.default_framework` maps to `StackConfig.framework`
- Environment variables override defaults
- PRD frontmatter overrides environment variables (priority: frontmatter > env > defaults)

### Acceptance Criteria

- [ ] `LLMClient` renamed from `PlannoClient`
- [ ] Retry logic works (3 retries with backoff)
- [ ] Timeout is configurable (default 120s)
- [ ] Error messages are clear and actionable
- [ ] `health_check()` returns True/False
- [ ] Streaming works for long responses
- [ ] Logging at appropriate levels
- [ ] All existing references to `PlannoClient` updated to `LLMClient`

---

## ISSUE 9: [TEST] Test Suite + Sample PRDs

**Labels:** `testing`, `priority:medium`
**Depends on:** #7

### Goal

Create test suite and sample PRD files to validate the full pipeline.

### Task 1: Sample PRD files

Create `tests/fixtures/` directory with sample PRDs:

**`tests/fixtures/prd_minimal.md`** — Minimal PRD:
- 1 feature (P0), greenfield, MVP scope
- Just a landing page

**`tests/fixtures/prd_medium.md`** — Medium complexity:
- 3-4 features (2x P0, 2x P1), greenfield, MVP scope
- Dashboard with multiple pages

**`tests/fixtures/prd_full.md`** — Full PRD:
- 6+ features (mixed priorities), greenfield, full scope
- Complete web app with auth, dashboard, settings

**`tests/fixtures/prd_extend.md`** — Extend mode:
- mode: extend, 2 features to add to existing project

### Task 2: Unit tests

**`tests/test_prd_parser.py`**
- Test frontmatter parsing (all fields)
- Test body section extraction
- Test feature extraction with priorities
- Test page route extraction
- Test validation warnings
- Test minimal PRD (doesn't crash)
- Test missing frontmatter (uses defaults)

**`tests/test_session.py`**
- Test init_session creates directory structure
- Test load_session restores state
- Test phase transitions
- Test version tracking (save_analysis v1, v2)
- Test resume after restart
- Test concurrent file operations don't corrupt

**`tests/test_config.py`**
- Test default settings
- Test env override
- Test get_settings caching

### Task 3: Integration test with mock LLM

**`tests/test_pipeline.py`**
- Mock LLMClient to return predetermined responses
- Test full pipeline: parse PRD → analyze → plan → generate
- Verify output files exist and are valid
- Test resume from each phase

### Task 4: Test configuration

**`tests/conftest.py`**
- Fixtures for temp directories
- Fixtures for sample PRD documents
- Mock LLM client fixture

### Acceptance Criteria

- [ ] All sample PRD files are valid and parseable
- [ ] `pytest tests/test_prd_parser.py` passes
- [ ] `pytest tests/test_session.py` passes
- [ ] `pytest tests/test_config.py` passes
- [ ] `pytest tests/test_pipeline.py` passes with mock LLM
- [ ] Coverage >= 60% on core modules
- [ ] Tests run in CI (no external dependencies needed)

---

## Instructions for Claude Code

### How to create GitHub Issues from this file:

```bash
# Run these commands to create all 10 issues:

gh issue create \ 
  --repo huaquanghan/orkit-crew \ 
  --title "[META] PRD-to-Product Pipeline — Brainstorm & Implementation Tracker" \ 
  --label "meta,tracking" \ 
  --body-file <(sed -n '/^## ISSUE 0:/,/^## ISSUE 1:/p' docs/IMPLEMENTATION_PLAN.md | head -n -1)

# Repeat for issues 1-9, extracting each section
# Or use the full descriptions above
```

### Recommended execution approach:

1. Create all 10 issues first
2. Work on issues sequentially following the dependency graph
3. Create a branch for each issue: `feat/issue-N-description`
4. Open PR when issue is complete
5. Update the META issue tracker after each completion

### Key constraints:

- Python 3.10+
- Use existing CrewAI framework (already a dependency)
- Use Pydantic v2 for all models
- Use Typer for CLI (not Click)
- Use Rich for console output
- Use python-frontmatter for PRD parsing
- All async code should use asyncio
- Follow existing code style: black formatter, 100 char line length
- Type hints on all functions (mypy strict mode)