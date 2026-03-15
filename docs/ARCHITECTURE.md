# Memory Hub v5 — Architecture Guide
> Last updated: 2026-03-15 | Version: v5.0.0

Technical architecture reference for humans and AI agents.

---

## System Overview

Memory Hub is a multi-agent persistent memory system that provides both REST API and MCP (Model Context Protocol) interfaces. It allows AI agents across different frameworks (LangChain, CrewAI, AutoGen) to store and retrieve long-term memories scoped by project and agent identity.

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI AGENTS                                │
│   Claude Code    OpenCode    Antigravity    Custom Agents        │
│       ↓              ↓           ↓              ↓                │
│   [MCP Tools]    [MCP Tools] [MCP Tools]   [REST API]           │
└───────┬──────────────┬───────────┬──────────────┬───────────────┘
        │              │           │              │
        ▼              ▼           ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TRANSPORT LAYER                              │
│   ┌─────────────────────┐    ┌──────────────────────────┐       │
│   │  MCP Server          │    │  FastAPI REST API         │       │
│   │  (stdio transport)   │    │  (HTTP on port 8000)      │       │
│   └──────────┬──────────┘    └────────────┬─────────────┘       │
└──────────────┼────────────────────────────┼─────────────────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MIDDLEWARE LAYER                             │
│   ┌───────────────┐  ┌─────────────────┐                        │
│   │ Auth Middleware │  │ Rate Limiter     │  (future)             │
│   │ (X-API-Key)    │  │ (per-endpoint)   │                       │
│   └───────┬───────┘  └────────┬────────┘                        │
└───────────┼───────────────────┼─────────────────────────────────┘
            │                   │
            ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                               │
│   ┌──────────────────┐  ┌──────────────────┐                    │
│   │ MemoryService     │  │ RegistryService   │                    │
│   │ - add()           │  │ - get_agent()      │                    │
│   │ - search()        │  │ - list_agents()    │                    │
│   │ - batch_add()     │  │ - validate_key()   │                    │
│   │ - delete()        │  └──────────────────┘                    │
│   │ - export()        │                                          │
│   └────────┬─────────┘                                          │
└────────────┼────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ADAPTER LAYER                               │
│   ┌──────────────────┐  (implements MemoryStore Protocol)       │
│   │ Mem0Adapter       │                                          │
│   │ - Gemini LLM      │  Future:                                 │
│   │ - Gemini Embed    │  ┌──────────────────┐                    │
│   │ - Qdrant vectors  │  │ CogneeAdapter     │                    │
│   └────────┬─────────┘  └──────────────────┘                    │
└────────────┼────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                               │
│   ┌──────────────────┐  ┌──────────────────┐                    │
│   │ Qdrant (vectors)  │  │ SQLite (metadata)  │                    │
│   │ 768-dim embeddings│  │ (via mem0)          │                    │
│   └──────────────────┘  └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
cognee-mcp/
├── src/memory_hub/
│   ├── __init__.py
│   ├── app.py                    # FastAPI app factory + lifespan
│   ├── config.py                 # Pydantic Settings (.env + YAML)
│   ├── interfaces/               # Protocol contracts
│   │   ├── memory_store.py       # MemoryStore Protocol
│   │   ├── agent_registry.py     # AgentRegistry Protocol
│   │   └── health_check.py       # HealthCheck Protocol
│   ├── models/                   # Pydantic data models
│   │   ├── domain.py             # MemoryEntry, SearchResult, AgentConfig
│   │   ├── requests.py           # MemoryAddRequest, SearchRequest
│   │   └── responses.py          # MemoryAddResponse, ErrorResponse
│   ├── services/                 # Business logic
│   │   ├── memory_service.py     # Scoped add/search/batch
│   │   ├── registry_service.py   # Agent config + key validation
│   │   └── health_service.py     # Health check implementation
│   ├── adapters/                 # Storage backends
│   │   └── mem0_adapter.py       # mem0 + Gemini Embedding 001
│   ├── middleware/               # Request processing
│   │   └── auth.py               # X-API-Key validation
│   └── transport/                # External interfaces
│       ├── rest/                  # FastAPI routes
│       │   ├── memory_routes.py
│       │   ├── health_routes.py
│       │   ├── agent_routes.py
│       │   └── deps.py           # Dependency injection
│       └── mcp/                  # MCP server for CLI agents
│           └── mcp_server.py
├── adapters/                     # Framework-specific wrappers
│   ├── langchain_tool.py         # LangChain BaseTool
│   ├── crewai_tool.py            # CrewAI Tool
│   └── autogen_tool.py           # AutoGen Tool
├── config/
│   ├── agents.yaml               # 9 agents, 4 projects
│   └── mcp/                      # MCP config examples
│       ├── claude_code.json
│       ├── opencode.json
│       └── antigravity.json
├── tests/
│   ├── unit/                     # 124 tests
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── QUICKSTART.md
│   ├── TROUBLESHOOTING.md
│   └── ARCHITECTURE.md
├── plans/
│   └── multi_agent_memory_plan_v5.md
├── pyproject.toml
├── uv.lock
├── .env.example
└── .gitignore
```

---

## Key Design Patterns

### 1. Protocol-Based Interfaces

Every service defines a Python `Protocol` class. Implementations are injected via constructors. This enables:
- **Easy testing:** Mock the protocol in unit tests
- **Backend swapping:** Replace mem0 with Cognee by implementing `MemoryStore`
- **No god modules:** Each file under 150 lines

### 2. Memory Scoping

Every memory operation is scoped to `project` + `agent_id`:
- `project` maps to mem0's `user_id` (isolates data between content-creation, seo-audit, personal, dev-tools)
- `agent_id` maps to mem0's `agent_id` (isolates data between agents in the same project)

### 3. App Factory Pattern

`create_app()` accepts optional pre-built services for testing:
```python
# Production — services built from .env
app = create_app()

# Testing — inject mocks
app = create_app(memory_service=mock_service, registry=mock_registry)
```

### 4. Dual Transport

Same business logic exposed via two interfaces:
- **REST API** — for framework agents (LangChain, CrewAI, AutoGen)
- **MCP Server** — for CLI agents (Claude Code, OpenCode, Antigravity)

---

## Agent Registry

| Agent ID | Framework | Project | Role |
|:---|:---|:---|:---|
| `research_agent` | LangChain | content-creation | Trend research + data collection |
| `writer_agent` | CrewAI | content-creation | Content writing + brainstorming |
| `video_agent` | AutoGen | content-creation | Video production pipeline |
| `seo_agent` | LangChain | seo-audit | SEO analysis + recommendations |
| `career_coach_agent` | LangChain | personal | Career guidance + goal tracking |
| `personal_assistant_agent` | CrewAI | personal | Calendar + tasks + reminders |
| `opencode_agent` | MCP | dev-tools | OpenCode CLI integration |
| `claude_code_agent` | MCP | dev-tools | Claude Code CLI integration |
| `antigravity_agent` | MCP | dev-tools | Antigravity IDE integration |

---

## Embedding Configuration

| Setting | Value | Rationale |
|:---|:---|:---|
| Provider | Gemini | Free tier, no OpenAI dependency |
| LLM Model | `gemini-2.5-flash` | Current stable model |
| Embedding Model | `gemini-embedding-001` | Stable, 100+ languages, Arabic-native |
| Dimensions | 768 | Half of OpenAI's 1536, saves RAM on 8GB machine |
| Vector Store | Qdrant (in-process) | No external service needed for MVP |

---

## Security Model

- **API Keys** stored in `.env` (never committed to git)
- **`HUB_API_KEY`** — master key, valid for all operations
- **`AGENT_KEYS`** — JSON map of per-agent keys to agent IDs
- **Auth Middleware** — validates `X-API-Key` header on every request
- **Public Paths** — `/health` and `/api/v1/health` bypass auth
- **MCP Auth** — agent identity from `AGENT_ID` + `AGENT_KEY` env vars at startup
