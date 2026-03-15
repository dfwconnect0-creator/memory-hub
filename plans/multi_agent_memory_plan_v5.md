# Memory Hub v5 — Implementation Plan

**Date:** March 15, 2026
**Author:** Mohamed + Antigravity (Pair Programming)
**Methodology:** Spec-Driven Development + Superpowers Workflow
**Status:** ✅ Approved

---

## Goal

Rebuild the Memory Hub from scratch using **spec-driven development** and professional software engineering practices. The hub serves as a single MCP server providing persistent memory for 9+ agents across 4 projects (`content-creation`, `seo-audit`, `personal`, `dev-tools`), running on an 8GB RAM MacBook.

This plan is what you (Mohamed) will execute step-by-step using Claude Code or OpenCode, following the Superpowers workflow.

---

## Part 1: Development Methodology

### Adopting Spec-Driven + Superpowers Workflow

Instead of "vibe coding" this project, we follow a structured pipeline. Here's how the two frameworks combine:

```
┌──────────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT PIPELINE                           │
│                                                                   │
│   SPEC-KIT                      SUPERPOWERS                      │
│   ─────────                     ────────────                     │
│   1. /speckit.constitution  →   Project principles               │
│   2. /speckit.specify       →   Brainstorming + interviews       │
│   3. /speckit.plan          →   Implementation plan (this doc)   │
│   4. /speckit.tasks         →   Bite-sized task breakdown        │
│   5. /speckit.implement     →   Subagent-driven TDD execution   │
│                                                                   │
│   Cross-cutting from Superpowers:                                │
│   • RED-GREEN-REFACTOR at every step                             │
│   • Code review between tasks                                    │
│   • Git worktrees for isolated branches                          │
│   • Evidence over claims (verify before declaring done)          │
└──────────────────────────────────────────────────────────────────┘
```

### Project Principles (Constitution)

These principles govern **every** implementation decision:

| Principle | Rule |
|:---|:---|
| **YAGNI** | Don't build it until you need it. Phase it. |
| **Test-First** | Write the failing test BEFORE the code. No exceptions. |
| **Single Responsibility** | Each module does ONE thing. Each function has ONE job. |
| **Dependency Injection** | Never hardcode dependencies. Inject services via constructors. |
| **Interface-First** | Define the contract (Protocol/ABC) before the implementation. |
| **Config as Code** | All config from YAML + .env. Zero magic strings in Python. |
| **8GB RAM Budget** | Every new dependency gets a RAM impact review. |
| **Evidence > Claims** | If the plan says it works, the test must prove it. |
| **Clean Imports** | No circular imports. Flat dependency graph. Import from interfaces. |
| **Explicit Errors** | Every error is typed, logged with trace ID, and returns ErrorResponse. |

---

## Part 2: Tooling Migration

### UV Over Pip

> [!IMPORTANT]
> The project currently uses `requirements.txt`. We migrate to `uv` + `pyproject.toml` completely.

#### Why UV

| Feature | pip | uv |
|:---|:---|:---|
| Speed | Slow | 10-100x faster |
| Lock files | Manual (pip-tools) | Built-in (`uv.lock`) |
| Virtual envs | Manual `venv` | Built-in `uv venv` |
| Python version management | pyenv | `uv python install` |
| Project management | None | `uv init`, `uv add`, `uv run` |

#### Migration Steps

```bash
# 1. Delete old tooling
rm requirements.txt

# 2. Initialize with uv
uv init --name memory-hub --python 3.12

# 3. Add core dependencies
uv add fastapi uvicorn[standard] pydantic pydantic-settings
uv add mem0ai python-dotenv pyyaml
uv add google-genai                      # Gemini Embedding 2 (free, Arabic-native)

# 4. Add dev dependencies
uv add --dev pytest pytest-asyncio pytest-cov httpx ruff mypy

# 5. Add MCP SDK
uv add mcp

# 6. Verify
uv run python -c "import fastapi; print('OK')"
```

#### pyproject.toml Shape

```toml
[project]
name = "memory-hub"
version = "0.1.0"
description = "Multi-agent persistent memory hub with MCP interface"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "mem0ai>=0.1.0",
    "google-genai>=1.0.0",            # Gemini Embedding 2
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0",
    "mcp>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=6.0",
    "httpx>=0.28",
    "ruff>=0.8",
    "mypy>=1.13",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "RUF"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.12"
strict = true
```

---

## Part 3: Architecture — Clean Modular Design

### Design Principles Applied

```
┌─────────────── Architecture Layers ──────────────────┐
│                                                       │
│  TRANSPORT LAYER (how requests arrive)                │
│  ├── REST API (FastAPI routes)                        │
│  └── MCP Server (for CLI/IDE agents)                  │
│       │                                               │
│       ▼                                               │
│  SERVICE LAYER (business logic)                       │
│  ├── MemoryService    ← Interface (Protocol)          │
│  ├── AgentRegistry    ← Interface (Protocol)          │
│  └── HealthService    ← Interface (Protocol)          │
│       │                                               │
│       ▼                                               │
│  STORAGE LAYER (data persistence)                     │
│  ├── Mem0Adapter      ← implements MemoryStore        │
│  └── (future: CogneeAdapter)                          │
│       │                                               │
│       ▼                                               │
│  INFRASTRUCTURE (cross-cutting)                       │
│  ├── Auth middleware                                  │
│  ├── Trace middleware                                 │
│  ├── Rate limiter                                     │
│  ├── Config loader                                    │
│  └── Structured logger                                │
└───────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Protocol-based interfaces**: Every service defines a Python `Protocol` class. Implementations are injected. This makes testing trivial (mock the protocol) and swapping mem0 for Cognee later is one file change.

2. **No god modules**: `server.py` (the current monolith) gets split into ~15 focused files. Each under 150 lines.

3. **Pydantic Settings**: All config (`.env` + YAML) flows through Pydantic `BaseSettings`, providing validation and type safety at startup — not at request time.

4. **Async everywhere**: All I/O operations are `async`. mem0 operations are wrapped in `asyncio.to_thread()` if they're synchronous.

5. **Gemini Embedding 2 as default embedder**: Free, Arabic-native (100+ languages), RAM-friendly (768 dims vs 1536), multimodal-ready for future video/audio memory.

### Embedding Configuration (mem0 + Gemini)

```python
# src/memory_hub/adapters/mem0_adapter.py — embedding config
mem0_config = {
    "embedder": {
        "provider": "google",
        "config": {
            "model": "gemini-embedding-002",
            "embedding_dims": 768,       # RAM-friendly for 8GB machine
            "api_key": settings.GEMINI_API_KEY,
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "memory_hub",
            "embedding_model_dims": 768,  # Must match embedder dims
        }
    }
}
```

```env
# .env — Gemini is the DEFAULT embedder (free tier)
GEMINI_API_KEY=your-gemini-api-key-here    # Get from https://aistudio.google.com/apikey
# OPENAI_API_KEY=sk-xxx                    # Optional: only if you want OpenAI as LLM provider
```

> [!TIP]
> **Why Gemini over OpenAI for embeddings?**
> - **Free** vs $0.13/M tokens
> - **Arabic-native** — critical for your Saudi/Gulf market content
> - **768 dims** — uses half the RAM of OpenAI's 1536 dims
> - **Multimodal** — future-ready for embedding video/audio memories
> - **Launched March 10, 2026** — Public Preview, production-ready via Gemini API

### File Structure

```
cognee-mcp/
├── .env.example                    # Template (committed)
├── .env                            # Secrets (gitignored)
├── .gitignore
├── .python-version                 # Python 3.12 (uv manages)
├── pyproject.toml                  # All deps, tools, config
├── uv.lock                         # Exact lockfile (committed)
├── README.md                       # Onboarding: 3 commands to running
│
├── config/
│   └── agents.yaml                 # Agent registry (no secrets!)
│
├── src/
│   └── memory_hub/
│       ├── __init__.py
│       ├── app.py                  # FastAPI app factory + lifespan
│       ├── config.py               # Pydantic Settings from .env + YAML
│       │
│       ├── interfaces/             # Protocol definitions (contracts)
│       │   ├── __init__.py
│       │   ├── memory_store.py     # Protocol: add, search, delete, export
│       │   ├── agent_registry.py   # Protocol: get_agent, list_agents, validate_key
│       │   └── health_check.py     # Protocol: check_health, get_metrics
│       │
│       ├── services/               # Business logic (implements interfaces)
│       │   ├── __init__.py
│       │   ├── memory_service.py   # Scoped memory ops (add, search, bulk)
│       │   ├── registry_service.py # YAML + .env agent loading
│       │   └── health_service.py   # Health + metrics aggregation
│       │
│       ├── adapters/               # Storage backends
│       │   ├── __init__.py
│       │   └── mem0_adapter.py     # mem0 wrapper implementing MemoryStore
│       │
│       ├── transport/              # API layers
│       │   ├── __init__.py
│       │   ├── rest/
│       │   │   ├── __init__.py
│       │   │   ├── memory_routes.py    # POST /memory, POST /memory/search, POST /memory/batch
│       │   │   ├── health_routes.py    # GET /health
│       │   │   ├── agent_routes.py     # GET /agents
│       │   │   └── export_routes.py    # GET /memory/export
│       │   └── mcp/
│       │       ├── __init__.py
│       │       └── mcp_server.py       # MCP tool definitions
│       │
│       ├── middleware/             # Cross-cutting concerns
│       │   ├── __init__.py
│       │   ├── auth.py             # API key verification
│       │   ├── tracing.py          # Trace ID generation + propagation
│       │   └── rate_limiter.py     # Per-agent, per-endpoint rate limiting
│       │
│       └── models/                 # Pydantic models (shared)
│           ├── __init__.py
│           ├── requests.py         # MemoryAddRequest, SearchRequest, BatchRequest
│           ├── responses.py        # MemoryResponse, SearchResponse, ErrorResponse
│           └── domain.py           # AgentConfig, MemoryCategory, etc.
│
├── adapters/                       # Framework-specific client adapters
│   ├── __init__.py
│   ├── langchain_tool.py           # LangChain MemoryTool
│   ├── crewai_tool.py              # CrewAI Tool
│   └── autogen_tool.py             # AutoGen Tool
│
├── tests/
│   ├── conftest.py                 # Shared fixtures (test client, mock registry)
│   ├── unit/
│   │   ├── test_config.py          # Config loading from .env + YAML
│   │   ├── test_auth.py            # API key validation
│   │   ├── test_memory_service.py  # Memory ops with mocked store
│   │   ├── test_registry.py        # Agent registry loading
│   │   └── test_models.py          # Pydantic model validation
│   ├── integration/
│   │   ├── test_memory_routes.py   # REST endpoints with real mem0
│   │   ├── test_isolation.py       # Cross-project isolation
│   │   └── test_rate_limiter.py    # Rate limiting behavior
│   └── e2e/
│       └── test_agent_workflow.py  # Full research→write→search flow
│
├── specs/                          # Spec-Driven Development artifacts
│   └── 001-memory-hub-mvp/
│       ├── spec.md                 # What + Why (functional spec)
│       ├── plan.md                 # How (this document, tech decisions)
│       ├── tasks.md                # Bite-sized task breakdown
│       └── research.md             # Tech stack research notes
│
├── .specify/                       # Spec-Kit config (if using specify CLI)
│   └── memory/
│       └── constitution.md         # Project principles
│
└── plans/                          # Historical plans (v3, v4 kept for reference)
    ├── multi_agent_memory_plan_v3.md
    ├── multi_agent_memory_plan_v4.md
    └── multi_agent_memory_plan_v5.md
```

> [!TIP]
> **Why `src/memory_hub/` instead of top-level `memory_hub/`?** The `src/` layout prevents accidental imports from the working directory. It's the recommended Python packaging layout.

---

## Part 4: Agent Registry Update

### All 9 Agents + CLI Agents

```yaml
# config/agents.yaml
agents:
  # ── content-creation ──────────────────────────
  research_agent:
    name: "Research Agent"
    framework: "langchain"
    project: "content-creation"
    role: "researcher"
    other_mcps: ["notebooklm", "web-scraper", "social-trends"]
    permissions: { read_shared: true, write_shared: true }

  writer_agent:
    name: "Writing Agent"
    framework: "crewai"
    project: "content-creation"
    role: "writer"
    other_mcps: ["notebooklm", "grammarly"]
    permissions: { read_shared: true, write_shared: true }

  video_agent:
    name: "Video Production Agent"
    framework: "autogen"
    project: "content-creation"
    role: "video-producer"
    other_mcps: ["remotion", "audio-mcp"]
    permissions: { read_shared: true, write_shared: false }

  # ── seo-audit ──────────────────────────────────
  seo_agent:
    name: "SEO Audit Agent"
    framework: "langchain"
    project: "seo-audit"
    role: "seo-analyst"
    other_mcps: ["google-search", "lighthouse", "ahrefs-api"]
    permissions: { read_shared: true, write_shared: true }

  # ── personal ───────────────────────────────────
  career_coach_agent:
    name: "Career Coach Agent"
    framework: "langchain"
    project: "personal"
    role: "career-coach"
    other_mcps: ["google-calendar", "linkedin-mcp", "notebooklm"]
    permissions: { read_shared: true, write_shared: true }

  personal_assistant_agent:
    name: "Personal Assistant Agent"
    framework: "crewai"
    project: "personal"
    role: "assistant"
    other_mcps: ["google-calendar", "gmail-mcp", "firebase"]
    permissions: { read_shared: true, write_shared: true }

  # ── CLI agents (MCP-native) ────────────────────
  opencode_agent:
    name: "OpenCode CLI Agent"
    framework: "mcp"
    project: "dev-tools"
    role: "opencode-cli"
    other_mcps: []
    permissions: { read_shared: true, write_shared: true }

  claude_code_agent:
    name: "Claude Code CLI Agent"
    framework: "mcp"
    project: "dev-tools"
    role: "claude-code-cli"
    other_mcps: []
    permissions: { read_shared: true, write_shared: true }

  antigravity_agent:
    name: "Antigravity IDE Agent"
    framework: "mcp"
    project: "dev-tools"
    role: "antigravity-ide"
    other_mcps: []
    permissions: { read_shared: true, write_shared: true }

settings:
  log_level: "INFO"
  max_memories_per_agent: 1000
  memory_ttl_days: 30
  memory_categories: [trend, brand, campaign, audience, career, task, code, general]
  rate_limits:
    memory_add: 60
    memory_search: 30
    memory_cognify: 5
```

### MCP Config for CLI Agents

**OpenCode** (`~/.config/opencode/config.json`):
```json
{
  "mcpServers": {
    "memory-hub": {
      "command": "uv",
      "args": ["run", "--project", "/Users/mohamedsalah/cognee-mcp", "python", "-m", "memory_hub.transport.mcp.mcp_server"],
      "env": {
        "AGENT_KEY": "mcp_opencode_xxxxxxxx",
        "AGENT_ID": "opencode_agent"
      }
    }
  }
}
```

**Claude Code** (`.claude/settings.json` or `CLAUDE.md`):
```json
{
  "mcpServers": {
    "memory-hub": {
      "command": "uv",
      "args": ["run", "--project", "/Users/mohamedsalah/cognee-mcp", "python", "-m", "memory_hub.transport.mcp.mcp_server"],
      "env": {
        "AGENT_KEY": "mcp_claude_xxxxxxxx",
        "AGENT_ID": "claude_code_agent"
      }
    }
  }
}
```

> [!NOTE]
> Both CLI agents use `uv run` to execute the MCP server. This ensures the correct virtual environment is always used, no activation needed.

---

## Part 5: Key Code Patterns

### Pattern 1: Interface-First Design

```python
# src/memory_hub/interfaces/memory_store.py
from typing import Protocol
from memory_hub.models.domain import MemoryEntry, SearchResult

class MemoryStore(Protocol):
    """Contract for any memory storage backend."""

    async def add(self, entry: MemoryEntry) -> str:
        """Store a memory, return its ID."""
        ...

    async def search(self, query: str, project: str,
                     agent_id: str | None = None, limit: int = 10) -> list[SearchResult]:
        """Search memories within scope."""
        ...

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        ...

    async def export(self, project: str) -> list[MemoryEntry]:
        """Export all memories for a project."""
        ...
```

### Pattern 2: Dependency Injection via App Factory

```python
# src/memory_hub/app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    config = load_config()
    registry = RegistryService(config)
    memory_store = Mem0Adapter(config)
    memory_service = MemoryService(store=memory_store, registry=registry)

    app.state.config = config
    app.state.registry = registry
    app.state.memory = memory_service

    yield
    # --- SHUTDOWN ---
    # cleanup if needed

def create_app() -> FastAPI:
    app = FastAPI(title="Memory Hub", lifespan=lifespan)
    app.include_router(memory_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.add_middleware(TraceMiddleware)
    return app
```

### Pattern 3: TDD (RED → GREEN → REFACTOR)

Every feature follows this cycle:

```python
# tests/unit/test_memory_service.py

# RED: Write the test FIRST — it should FAIL
async def test_add_memory_scoped_to_project(mock_store):
    service = MemoryService(store=mock_store)
    result = await service.add(content="Test", project="content-creation", agent_id="research_agent")

    # Assert the store was called with correct scoping
    mock_store.add.assert_called_once()
    call_args = mock_store.add.call_args[0][0]
    assert call_args.project == "content-creation"
    assert call_args.agent_id == "research_agent"

# GREEN: Write minimal code to make it pass
# REFACTOR: Clean up without changing behavior
```

---

## Part 6: Implementation Phases

### Phase 0: Project Bootstrap (30 min)

```
□ Delete server.py, requirements.txt (backup to plans/)
□ Run: uv init --name memory-hub --python 3.12
□ Create src/memory_hub/ directory structure
□ Create config/agents.yaml
□ Create .env.example and .gitignore
□ Create .specify/memory/constitution.md with principles
□ Run: git init && git add -A && git commit -m "chore: bootstrap v5 with uv"
```

### Phase 1: Core Interfaces + Config (1 day)

**TDD target: 100% of interfaces and config loading**

```
□ Write interfaces: MemoryStore, AgentRegistry, HealthCheck
□ Write Pydantic models: requests, responses, domain
□ Write config.py: load from .env + YAML with validation
□ Write tests FIRST for each:
  - test_config.py: loads .env, validates required fields, rejects bad YAML
  - test_models.py: validates MemoryAddRequest, rejects bad categories
□ Verify: uv run pytest tests/unit/ -v  (all pass)
□ Git commit: "feat(core): interfaces, models, and config"
```

### Phase 2: Memory Service + Auth (1-2 days)

```
□ Implement Mem0Adapter (implements MemoryStore protocol)
□ Implement MemoryService (scoped add/search/batch)
□ Implement RegistryService (agent loading + key validation)
□ Implement middleware: auth, tracing, rate limiter
□ Tests FIRST:
  - test_memory_service.py: scoped add, scoped search, batch add
  - test_auth.py: valid key accepts, invalid rejects, missing header 403
  - test_isolation.py: project A can't see project B memories
□ Verify: uv run pytest tests/ -v --cov=memory_hub (>80% coverage)
□ Git commit: "feat(service): memory service + auth middleware"
```

### Phase 3: REST API (1 day)

```
□ Wire routes using FastAPI app factory
□ Implement: POST /memory, POST /memory/search, POST /memory/batch
□ Implement: GET /health, GET /agents, GET /memory/export
□ Tests FIRST:
  - test_memory_routes.py: full request/response cycle
  - test_health_routes.py: returns correct shape
□ Verify: uv run pytest tests/ -v && uv run ruff check src/
□ Manual test: uv run uvicorn memory_hub.app:create_app --factory --port 8000
□ Git commit: "feat(api): REST endpoints"
```

### Phase 4: MCP Server (1 day)

```
□ Implement MCP server with memory_add, memory_search, memory_status tools
□ Create MCP config files for OpenCode + Claude Code + Antigravity
□ Test MCP server manually with a CLI agent
□ Git commit: "feat(mcp): MCP server interface for CLI agents"
```

### Phase 5: Framework Adapters (1 day)

```
□ Implement LangChain MemoryTool adapter
□ Implement CrewAI Tool adapter
□ Implement AutoGen Tool adapter
□ Each adapter: <100 lines, points to REST API, injects scoping
□ Test each adapter with a minimal agent script
□ Git commit: "feat(adapters): LangChain, CrewAI, AutoGen adapters"
```

### Phase 6: Polish + Documentation (1 day)

```
□ Write README.md (setup, usage, agent registration)
□ Run full suite: uv run pytest tests/ -v --cov=memory_hub
□ Run linter: uv run ruff check src/ tests/
□ Run type checker: uv run mypy src/
□ Create .specify/ spec artifacts for the project record
□ Final git commit: "docs: README + project docs"
```

---

## Part 7: Software Engineering Practices Enforced

| Practice | How It's Enforced |
|:---|:---|
| **SOLID Principles** | Protocols for interfaces, single-responsibility modules, dependency injection |
| **TDD** | pytest + Superpowers RED-GREEN-REFACTOR; no feature without a test |
| **Clean Code** | Ruff linter with strict rules, max 100 chars/line, no unused imports |
| **Type Safety** | mypy strict mode, all function signatures typed |
| **No Dead Code** | Every YAML field used in code; every import used; ruff catches the rest |
| **Structured Logging** | JSON logs with trace ID, agent ID, latency |
| **Error Handling** | ErrorResponse model, no raw string exceptions |
| **Git Hygiene** | Conventional commits, one feature per branch, worktrees for parallel work |
| **Dependency Audit** | RAM budget check before adding any new package |
| **Code Reviews** | Superpowers-style: after each task, review against plan |

---

## Verification Plan

### Automated Tests

Run all at any point during development:

```bash
# Unit tests (fast, no external deps)
uv run pytest tests/unit/ -v

# Integration tests (needs mem0 running)
uv run pytest tests/integration/ -v

# Full suite with coverage
uv run pytest tests/ -v --cov=memory_hub --cov-report=term-missing

# Linting
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

### Critical Test Cases

| Test | What It Proves |
|:---|:---|
| `test_isolation.py::test_project_cross_contamination` | Project A memories invisible to project B search |
| `test_auth.py::test_invalid_key_rejected` | Auth middleware blocks unauthorized requests |
| `test_memory_service.py::test_scoped_add` | Every `memory.add()` includes project + agent_id |
| `test_memory_routes.py::test_search_is_post` | Search uses POST (not GET with body) |
| `test_config.py::test_missing_env_var_fails_startup` | Missing GEMINI_API_KEY crashes at boot, not at request time |
| `test_rate_limiter.py::test_rate_exceeded_returns_429` | Agent exceeding limit gets ErrorResponse |

### Manual Verification

After Phase 3, test manually with:

```bash
# 1. Start server
uv run uvicorn memory_hub.app:create_app --factory --port 8000

# 2. Health check
curl http://localhost:8000/api/v1/health

# 3. Add a memory (with auth)
curl -X POST http://localhost:8000/api/v1/memory \
  -H "Content-Type: application/json" \
  -H "X-API-Key: lc_research_a8f3k2m1" \
  -d '{"content": "TikTok trending: Ramadan content +40%", "project": "content-creation", "category": "trend"}'

# 4. Search (POST, not GET!)
curl -X POST http://localhost:8000/api/v1/memory/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: lc_research_a8f3k2m1" \
  -d '{"query": "ramadan trends", "project": "content-creation"}'

# 5. Verify isolation: search with SEO agent key should NOT find content-creation memories
curl -X POST http://localhost:8000/api/v1/memory/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: lc_seo_d5i6n5p4" \
  -d '{"query": "ramadan trends", "project": "seo-audit"}'
# Expected: empty results (different project)
```

---

## Part 8: How to Execute This Plan

> [!IMPORTANT]
> **You (Mohamed) execute this.** Here's your workflow:

### Option A: With Claude Code + Superpowers

```bash
# 1. Install superpowers plugin
/install-plugin superpowers

# 2. Navigate to project
cd ~/cognee-mcp

# 3. Start Claude Code
claude

# 4. Give it this plan
# Paste: "Execute the v5 implementation plan in plans/multi_agent_memory_plan_v5.md.
#          Follow the Superpowers workflow: write tests first, then implement,
#          then review. Start with Phase 0."
```

### Option B: With OpenCode

```bash
# 1. Navigate to project
cd ~/cognee-mcp

# 2. Start OpenCode
opencode

# 3. Give it the same plan reference
```

### Option C: Phase by phase with any agent

Follow the numbered phases. After each phase:
1. Run `uv run pytest` — all tests must pass
2. Run `uv run ruff check src/` — zero lint errors
3. Commit with conventional commit message
4. Move to next phase

---

## Summary: What's New in v5 vs v4

| Area | v4 | v5 |
|:---|:---|:---|
| **Methodology** | Ad-hoc plan | Spec-Driven + Superpowers TDD |
| **Package Manager** | pip + requirements.txt | uv + pyproject.toml + uv.lock |
| **Architecture** | Described in prose | Clean modular with interfaces/services/adapters |
| **Testing** | Mentioned in checklist | Strict TDD with pytest, coverage, ruff, mypy |
| **CLI Agents** | Not included | OpenCode + Claude Code with MCP configs |
| **Code Quality** | Guidelines checklist | Enforced via ruff, mypy, Superpowers code review |
| **Agent Count** | 3 agents, 1 project | 9 agents, 4 projects |
| **Memory Features** | Basic add/search | + batch, export, categories, TTL |
| **File Structure** | Flat (server.py) | src/ layout with 15+ focused modules |
