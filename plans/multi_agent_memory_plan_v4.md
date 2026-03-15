# Multi-Agent Memory Architecture Plan (v4)

**Date:** March 9, 2026  
**Status:** Draft  
**Constraint:** MacBook 8GB RAM — every architectural decision must respect this limit.

---

## 1. Problem Statement

We need a **persistent memory hub** that lets ~10 AI agents (across LangChain, CrewAI, AutoGen, and MCP-native IDE agents) store, search, and share long-term knowledge — without overloading an 8GB RAM machine.

### What v3 Got Wrong (Post-Mortem)

> [!NOTE]
> **What is a "post-mortem"?** It's a practice from engineering teams where, after something goes wrong, you write down exactly *what* broke and *why* — not to blame anyone, but so you never make the same mistake twice. Think of it as a "lessons learned" doc. We're baking v3's post-mortem directly into v4 so any developer (including future-you) sees these warnings before writing a single line of code.

> [!CAUTION]
> **For the developer**: These are real mistakes from the v3 plan that burned time. Use this checklist when writing any future plan.

| Rule | What Went Wrong in v3 | In Plain Terms |
| :--- | :--- | :--- |
| **Plan must match code** | Plan said "load keys from YAML", code hardcoded them in a Python set | The doc said one thing, the code did another — confusing for everyone |
| **Don't claim features you haven't built** | Plan said "project-scoped isolation", but `cognee.add()` was called with zero scoping | We promised data wouldn't mix between projects, but it did |
| **Use correct HTTP semantics** | Used `GET` with a request body for search — breaks behind proxies | Used the wrong HTTP method, causing silent failures |
| **Align schemas** | `agents.yaml` used `type` instead of `framework`, had undocumented `isolation` field | Config files disagreed with the code |
| **Don't advertise interfaces you won't build** | Project called "cognee-mcp" but no MCP server existed in the roadmap | Named the whole project after a feature that didn't exist |
| **Test every claim** | "Three Metrics" debugging dashboard was a Phase 4 idea with no technical design | Promised a dashboard with zero plan on how to build it |

---

## 2. Technology Decision: mem0 (Primary) + Optional Cognee

### Why mem0 for an 8GB RAM Machine

| Criteria | mem0 | Cognee |
| :--- | :--- | :--- |
| **RAM footprint** | Light — SQLite + CPU-only, no GPU | Heavy — runs LanceDB + Kuzu + SQLite in-process, graph grows fast |
| **Default storage** | SQLite (`~/.mem0/history.db`) | SQLite + LanceDB + Kuzu (3 embedded DBs) |
| **Token savings** | Up to 80–97% token reduction | Full knowledge graph (richer, but more expensive) |
| **Setup complexity** | `pip install mem0ai` + API key | `pip install cognee` + API key + `.env` for 3 stores |
| **Multi-agent scoping** | Built-in `user_id`, `agent_id`, `run_id` scopes | Requires manual dataset naming |
| **Framework integrations** | LangChain, CrewAI, AutoGen, AWS Agent SDK | LangChain, generic REST |

### Recommendation

```
┌─────────────────────────────────────────────────┐
│  PRIMARY:  mem0 (all day-to-day memory ops)     │
│  OPTIONAL: Cognee (deep reasoning, knowledge    │
│            graphs — only when needed, run async) │
└─────────────────────────────────────────────────┘
```

- **Start with mem0 only.** It handles 90% of the use case.
- **Add Cognee later** (Phase 4+) only if you need multi-hop reasoning across large document sets.
- **Never run both simultaneously** on an 8GB machine.

---

## 3. Architecture: "The Memory Hub"

```
┌──────────────────────────────────────────────────────────────────┐
│                        MEMORY HUB (FastAPI)                      │
│                         localhost:8000                            │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ Auth       │  │ Trace ID     │  │ Rate Limiter             │ │
│  │ Middleware │→ │ Middleware   │→ │ (per agent, per minute)  │ │
│  └────────────┘  └──────────────┘  └──────────────────────────┘ │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     REST API (v1)                         │  │
│  │                                                           │  │
│  │  POST /api/v1/memory          → Add memory               │  │
│  │  POST /api/v1/memory/search   → Search memory  (POST!)   │  │
│  │  POST /api/v1/memory/cognify  → Trigger enrichment       │  │
│  │  GET  /api/v1/health          → Health check              │  │
│  │  GET  /api/v1/agents          → List registered agents    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     MCP Server Interface                   │  │
│  │                                                           │  │
│  │  Tool: memory_add       → Same as POST /memory            │  │
│  │  Tool: memory_search    → Same as POST /memory/search     │  │
│  │  Tool: memory_status    → Health + agent metrics           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────┐  ┌────────────────────────────────────┐  │
│  │  Agent Registry   │  │  mem0 Memory Layer                 │  │
│  │  (agents.yaml)    │  │  ┌──────────┐ ┌─────────────────┐ │  │
│  │                   │  │  │ SQLite   │ │ Qdrant (local)  │ │  │
│  │  Loaded at        │  │  │ (history)│ │ or in-memory    │ │  │
│  │  startup, cached  │  │  └──────────┘ │ vector store    │ │  │
│  └───────────────────┘  │               └─────────────────┘ │  │
│                          └────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘

         ▲               ▲               ▲               ▲               ▲
         │               │               │               │               │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐    ┌──────┴──────┐
    │LangChain│    │ CrewAI  │    │AutoGen  │    │MCP IDE  │    │  Personal   │
    │  Agents │    │  Agents │    │  Agents │    │ Agents  │    │   Agents    │
    │         │    │         │    │         │    │(Cursor, │    │career-coach │
    │research │    │ writer  │    │ video   │    │Antigrav.)│    │ assistant  │
    │ seo     │    │assistant│    │         │    │         │    │             │
    └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────────┘
```

---

## 4. Agent Registry Schema (agents.yaml)

### Multi-Project, Single MCP Server

All agents connect to **one Memory Hub server**. The `project` field isolates their data:

```
┌───────────────────────── ONE Memory Hub MCP ──────────────────────────┐
│                                                                       │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ content-creation │  │ seo-audit    │  │ personal                 │  │
│  │                  │  │              │  │                          │  │
│  │ research_agent   │  │ seo_agent    │  │ career_coach_agent       │  │
│  │ writer_agent     │  │ audit_agent  │  │ personal_assistant_agent │  │
│  │ video_agent      │  │              │  │                          │  │
│  └─────────────────┘  └──────────────┘  └──────────────────────────┘  │
│      ISOLATED             ISOLATED              ISOLATED              │
└───────────────────────────────────────────────────────────────────────┘
```

```yaml
# config/agents.yaml
# ---------------------------------------------------------
# RULE: Every field here MUST be used by the server code.
#       If it's not used, delete it. No dead config.
# ---------------------------------------------------------

# =============================================
# PROJECT: content-creation
# Pipeline: research → writer → video
# =============================================
agents:
  research_agent:
    name: "Research Agent"
    framework: "langchain"       # langchain | crewai | autogen | mcp
    project: "content-creation"  # Scopes all memory reads/writes
    role: "researcher"           # For display + logging
    other_mcps: ["notebooklm", "web-scraper", "social-trends"]
    permissions:
      read_shared: true          # Can this agent read shared project memory?
      write_shared: true         # Can this agent write to shared project memory?

  writer_agent:
    name: "Writing Agent"
    framework: "crewai"
    project: "content-creation"
    role: "writer"
    other_mcps: ["notebooklm", "grammarly"]
    permissions:
      read_shared: true
      write_shared: true

  video_agent:
    name: "Video Production Agent"
    framework: "autogen"
    project: "content-creation"
    role: "video-producer"
    other_mcps: ["remotion", "audio-mcp"]
    permissions:
      read_shared: true
      write_shared: false         # Read-only — consumes but doesn't pollute

  # =============================================
  # PROJECT: seo-audit
  # Pipeline: crawl → analyze → report
  # =============================================
  seo_agent:
    name: "SEO Audit Agent"
    framework: "langchain"
    project: "seo-audit"
    role: "seo-analyst"
    other_mcps: ["google-search", "lighthouse", "ahrefs-api"]
    permissions:
      read_shared: true
      write_shared: true

  # =============================================
  # PROJECT: personal
  # Agents for personal productivity & growth
  # =============================================
  career_coach_agent:
    name: "Career Coach Agent"
    framework: "langchain"
    project: "personal"
    role: "career-coach"
    other_mcps: ["google-calendar", "linkedin-mcp", "notebooklm"]
    permissions:
      read_shared: true
      write_shared: true

  personal_assistant_agent:
    name: "Personal Assistant Agent"
    framework: "crewai"
    project: "personal"
    role: "assistant"
    other_mcps: ["google-calendar", "gmail-mcp", "firebase"]
    permissions:
      read_shared: true
      write_shared: true

settings:
  log_level: "INFO"
  max_memories_per_agent: 1000    # Prevent runaway storage on 8GB machine
  memory_ttl_days: 30             # Auto-expire old memories (0 = never expire)
  memory_categories:              # Valid categories for memory tagging
    - trend         # Short-lived market/social insights
    - brand         # Permanent brand guidelines & identity
    - campaign      # Campaign results & analytics
    - audience      # Audience segments & behavior
    - career        # Career goals, skills, milestones
    - task          # Personal tasks, reminders, follow-ups
    - general       # Default catch-all
  rate_limits:
    memory_add: 60                # Writes/min (high for research sweeps)
    memory_search: 30             # Reads/min
    memory_cognify: 5             # Heavy ops/min
```

> [!IMPORTANT]
> **API keys go in `.env`, NEVER in YAML or Python code.** See Section 6.
> The `other_mcps` field is **informational only** — it documents what other MCP servers each agent uses, but the Memory Hub doesn't manage those connections.

---

## 5. Data Isolation Model

This is the **#1 thing v3 got wrong**. Here's how it actually works with mem0:

### Three Scoping Levels

```
┌─────────────────────────────────────────────────┐
│  Level 1: PROJECT SCOPE                         │
│  ┌────────────────────────────────────────────┐ │
│  │  project = "content-creation"              │ │
│  │                                            │ │
│  │  Level 2: AGENT SCOPE                      │ │
│  │  ┌──────────────┐ ┌──────────────────────┐│ │
│  │  │ research_01  │ │ writer_01            ││ │
│  │  │ (private     │ │ (private memories)   ││ │
│  │  │  memories)   │ │                      ││ │
│  │  └──────────────┘ └──────────────────────┘│ │
│  │                                            │ │
│  │  Level 3: SHARED PROJECT MEMORY            │ │
│  │  ┌──────────────────────────────────────┐  │ │
│  │  │ Shared pool (agents with             │  │ │
│  │  │ write_shared=true can contribute)    │  │ │
│  │  └──────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Code Pattern: Scoped Memory Operations

```python
from mem0 import Memory

memory = Memory()  # Uses defaults: SQLite + Qdrant local

# --- ADD MEMORY (always scoped) ---
async def add_memory(agent_id: str, project: str, content: str):
    """Every memory write MUST include user_id (maps to project) and agent_id."""
    memory.add(
        content,
        user_id=project,       # Level 1: project scope
        agent_id=agent_id,     # Level 2: agent scope
        metadata={"project": project, "agent_id": agent_id}
    )

# --- SEARCH MEMORY (scoped to project, optionally to agent) ---
async def search_memory(agent_id: str, project: str, query: str, shared: bool = False):
    """Search within scope. If shared=True, search entire project."""
    if shared:
        # Search all memories in the project (cross-agent)
        results = memory.search(query, user_id=project)
    else:
        # Search only this agent's memories
        results = memory.search(query, user_id=project, agent_id=agent_id)
    return results
```

> [!WARNING]
> **Never call `memory.add(content)` without scoping.** That's how v3 broke — every agent's memories mixed together.

---

## 6. Security: API Keys and Auth

### .env File (The Only Place for Secrets)

```env
# .env — NEVER commit this to git
# -----------------------------------

# Agent API Keys (format: <framework>_<role>_<random>)
# --- content-creation project ---
AGENT_KEY_RESEARCH=lc_research_a8f3k2m1
AGENT_KEY_WRITER=crew_writer_b7g4l3n2
AGENT_KEY_VIDEO=ag_video_c6h5m4o3
# --- seo-audit project ---
AGENT_KEY_SEO_ANALYST=lc_seo_d5i6n5p4
# --- personal project ---
AGENT_KEY_CAREER_COACH=lc_career_e4j7o6q5
AGENT_KEY_ASSISTANT=crew_asst_f3k8p7r6

# mem0 config
MEM0_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxx

# Server config
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO
```

### Code Pattern: Loading Keys from .env + YAML

```python
import os
import yaml
from dotenv import load_dotenv

load_dotenv()  # Load .env file

def load_agent_registry():
    """Load agents from YAML, then attach API keys from environment."""
    with open("config/agents.yaml") as f:
        config = yaml.safe_load(f)

    # Build a lookup: api_key -> agent_config
    registry = {}
    for agent_id, agent_config in config["agents"].items():
        # Key naming convention: AGENT_KEY_{ROLE_UPPER}
        env_key = f"AGENT_KEY_{agent_config['role'].upper().replace('-', '_')}"
        api_key = os.getenv(env_key)
        if not api_key:
            raise ValueError(f"Missing env var {env_key} for agent {agent_id}")
        agent_config["agent_id"] = agent_id
        registry[api_key] = agent_config

    return registry

# Usage in auth middleware:
AGENT_REGISTRY = load_agent_registry()

async def verify_api_key(x_api_key: str = Header(...)):
    agent = AGENT_REGISTRY.get(x_api_key)
    if not agent:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return agent  # Returns full agent config, not just the key
```

---

## 7. Agent Communication Strategy

Based on your requirement for **research agent → writing agent → video agent** workflows:

### Option A: Shared Memory (Recommended for Your Scale)

Agents don't talk directly. Instead, they **read and write to project-scoped shared memory**. This avoids context overload because each agent only pulls what it needs.

```
Research Agent                Shared Project Memory         Writer Agent
     │                              │                           │
     │──── writes findings ────────▶│                           │
     │                              │◀────── reads findings ────│
     │                              │                           │
     │                              │──── writes draft ────────▶│ (to shared)
     │                              │                           │
     │                              │        Video Agent        │
     │                              │◀── reads final draft ─────│
```

**Why this works better than direct agent-to-agent:**
- No n² connections (10 agents = 90 direct channels vs 1 shared pool)
- Each agent only retrieves relevant memories via semantic search
- No framework compatibility issues (LangChain doesn't need to "speak" AutoGen)
- Natural audit trail — everything is searchable

### Option B: Message Passing (Future, when needed)

If you later need real-time agent-to-agent handoffs, add a **message queue endpoint** to the Memory Hub:

```python
# Future: POST /api/v1/messages
class AgentMessage(BaseModel):
    from_agent: str
    to_agent: str
    type: str         # "handoff" | "request" | "notification"
    payload: dict
    project: str
```

> **Start with Option A.** Only add Option B if you find agents need synchronous coordination.

---

## 8. MCP Server Interface

For IDE agents (Antigravity, Cursor, Windsurf, CLI tools), expose the Memory Hub as an MCP server:

### Tool Definitions

```python
# mcp_server.py — MCP wrapper around the same memory logic

from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("memory-hub")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="memory_add",
            description="Store a memory scoped to your agent and project",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The information to remember"},
                    "project": {"type": "string", "description": "Project slug"},
                    "shared": {"type": "boolean", "default": False,
                               "description": "Write to shared project memory?"}
                },
                "required": ["content", "project"]
            }
        ),
        Tool(
            name="memory_search",
            description="Search memories. Returns relevant past context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"},
                    "project": {"type": "string", "description": "Project slug"},
                    "shared": {"type": "boolean", "default": True,
                               "description": "Search shared project memory too?"}
                },
                "required": ["query", "project"]
            }
        ),
        Tool(
            name="memory_status",
            description="Check memory hub health and usage for your project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"}
                },
                "required": ["project"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "memory_add":
        # Delegate to same mem0 logic as REST API
        result = await add_memory(
            agent_id=server.agent_id,  # From MCP auth
            project=arguments["project"],
            content=arguments["content"],
        )
        return [TextContent(type="text", text=f"Memory stored. ID: {result['id']}")]

    elif name == "memory_search":
        results = await search_memory(
            agent_id=server.agent_id,
            project=arguments["project"],
            query=arguments["query"],
            shared=arguments.get("shared", True)
        )
        return [TextContent(type="text", text=format_results(results))]
```

### MCP Config for IDEs

```json
{
  "mcpServers": {
    "memory-hub": {
      "command": "python",
      "args": ["-m", "memory_hub.mcp_server"],
      "env": {
        "AGENT_KEY": "ag_main_xxxxxxxx",
        "AGENT_ID": "antigravity_001"
      }
    }
  }
}
```

---

## 9. Request Logging & Trace IDs

Every request gets a trace ID. This is **non-negotiable** for debugging multi-agent systems.

```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id

        logger.info(f"[{trace_id}] {request.method} {request.url.path}",
                     extra={"trace_id": trace_id,
                            "agent": getattr(request.state, "agent_id", "unknown")})

        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response
```

### Structured Log Format

```json
{
  "timestamp": "2026-03-09T14:30:00Z",
  "trace_id": "a1b2c3d4-e5f6-7890",
  "agent_id": "research_agent",
  "project": "content-creation",
  "action": "memory_add",
  "status": "success",
  "latency_ms": 45
}
```

---

## 10. Error Response Schema

All API errors must follow this shape. No more raw strings.

```python
from pydantic import BaseModel
from typing import Optional

class ErrorResponse(BaseModel):
    error: str           # Machine-readable: "UNAUTHORIZED", "RATE_LIMITED", "INTERNAL"
    message: str         # Human-readable explanation
    trace_id: Optional[str] = None
    agent_id: Optional[str] = None

# Usage:
raise HTTPException(
    status_code=429,
    detail=ErrorResponse(
        error="RATE_LIMITED",
        message=f"Agent {agent_id} exceeded {limit}/min rate limit",
        trace_id=request.state.trace_id
    ).model_dump()
)
```

---

## 11. Implementation Roadmap

| Phase | Title | Deliverables | Est. Time |
| :---: | :--- | :--- | :---: |
| **1** | **Foundation** | FastAPI server, `.env` + YAML auth, trace middleware, health endpoint, error schema | 2–3 days |
| **2** | **mem0 Integration** | mem0 wired up with scoped `add`/`search`, data isolation tests, rate limiter | 2–3 days |
| **3** | **Framework Adapters** | LangChain `MemoryTool`, CrewAI `Tool`, AutoGen `Tool` — all pointing to REST API | 2 days |
| **4** | **MCP Server** | MCP interface for IDE agents, config files for Cursor/Antigravity | 2 days |
| **5** | **Shared Memory & Coordination** | Cross-agent shared memory pool, project-level search, agent message queue (if needed) | 2–3 days |
| **6** | **Debug Dashboard** | CLI tool showing heartbeat, ingestion stats, retrieval latency per agent. Web UI optional. | 2 days |

### Phase 1 Checklist (Start Here)

```
□ Initialize project: pyproject.toml with deps
□ Create .env.example (never commit .env)
□ Create .gitignore (include .env, __pycache__, *.db)
□ Implement load_agent_registry() from YAML + .env
□ Implement verify_api_key middleware
□ Implement TraceMiddleware
□ Add GET /api/v1/health endpoint
□ Add ErrorResponse model
□ Use lifespan context manager (NOT @app.on_event)
□ Write first test: auth accepts valid key, rejects invalid
```

---

## 12. RAM Budget (8GB Constraint)

| Component | Est. Memory | Notes |
| :--- | :--- | :--- |
| macOS + system | ~3 GB | Non-negotiable |
| Python + FastAPI | ~100 MB | Lightweight |
| mem0 (SQLite + in-memory vectors) | ~200–500 MB | Depends on memory count |
| IDE (VS Code / Cursor) | ~500 MB–1 GB | Running simultaneously |
| LLM API calls | ~0 MB | Cloud-based, no local model |
| **Total estimated** | **~4–5 GB** | **Leaves ~3 GB headroom** |

> [!WARNING]
> If you ever add Cognee or a local LLM (Ollama), the budget changes dramatically. A local 7B model needs ~4–6 GB alone. **Don't do this on 8GB RAM.**

---

## 13. File Structure

```
cognee-mcp/
├── .env.example              # Template (committed)
├── .env                      # Actual secrets (gitignored)
├── .gitignore
├── pyproject.toml
├── config/
│   └── agents.yaml           # Agent registry (no secrets!)
├── memory_hub/
│   ├── __init__.py
│   ├── main.py               # FastAPI app + lifespan
│   ├── auth.py               # Registry loader + auth middleware
│   ├── middleware.py          # Trace ID + rate limiter
│   ├── routes/
│   │   ├── memory.py         # POST /memory, POST /memory/search
│   │   ├── health.py         # GET /health
│   │   └── agents.py         # GET /agents
│   ├── services/
│   │   └── memory_service.py # mem0 wrapper with scoping logic
│   ├── models/
│   │   ├── requests.py       # Pydantic request models
│   │   └── responses.py      # Pydantic response + error models
│   └── mcp_server.py         # MCP interface (Phase 4)
├── adapters/
│   ├── langchain_tool.py     # CogneeMemoryTool for LangChain
│   ├── crewai_tool.py        # Memory Tool for CrewAI
│   └── autogen_tool.py       # Memory Tool for AutoGen
├── tests/
│   ├── test_auth.py
│   ├── test_memory.py
│   └── test_isolation.py     # Critical: proves scoping works
├── plans/
│   └── multi_agent_memory_plan_v4.md
└── logs/                     # Structured JSON logs
```

---

## 14. Developer Guidelines Checklist

Use this checklist when **planning any future version**.

```
□ Every config field in YAML is used in code (no dead fields)
□ Every feature claimed in the plan has a code path
□ Secrets are in .env, never in code or YAML
□ All write operations are scoped (project + agent_id)
□ All search operations are scoped (project, optionally agent_id)
□ HTTP methods match semantics (POST for writes+search, GET for reads)
□ Every request gets a trace ID
□ All errors use the ErrorResponse schema
□ RAM budget reviewed before adding any new dependency
□ Tests exist for: auth, scoping, isolation, error cases
□ .gitignore covers: .env, *.db, __pycache__, logs/
□ README includes: setup steps, .env.example, how to register new agent
```
