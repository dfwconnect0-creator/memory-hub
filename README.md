# Memory Hub v5

Persistent, cross-agent memory for multi-agent AI systems.
Agents store and retrieve memories scoped to their **project** via a REST API or an MCP server.
Backed by [mem0](https://github.com/mem0ai/mem0) with Google Gemini Embedding 2 (`gemini-embedding-002`, 768 dims).

---

## Features

- **REST API** — FastAPI app with project-scoped `POST /memory`, `POST /memory/search`, `POST /memory/batch`, `GET /health`, `GET /agents`, `GET /memory/export`
- **MCP Server** — FastMCP tools (`memory_add`, `memory_search`, `memory_status`) for Claude Code, OpenCode, and Antigravity IDE
- **Framework Adapters** — Drop-in tools for LangChain, CrewAI, and AutoGen
- **Auth** — Per-agent API keys; project scope locked at runtime, not caller-supplied
- **Gemini Embedding 2** — Free-tier `gemini-embedding-002` (768 dims) via `GEMINI_API_KEY`

---

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- A Google AI API key (Gemini — free tier works)

### Installation

```bash
git clone <this-repo>
cd cognee-mcp
uv sync
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here
HUB_API_KEY=your_hub_master_key_here

# Agent keys — JSON map of api_key → agent_id
AGENT_KEYS={"lc_research_a8f3k2m1": "research_agent", "crew_writer_xxx": "writer_agent"}

# Optional
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
AGENTS_YAML_PATH=config/agents.yaml
```

> Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey).

### Run the REST API

```bash
uv run uvicorn memory_hub.app:app --reload
```

Or use the app factory directly:

```python
from memory_hub.app import create_app
app = create_app()
```

### Run the MCP Server

```bash
uv run python -m memory_hub.transport.mcp.mcp_server
```

Set agent identity via environment:

```bash
AGENT_ID=claude_code_agent AGENT_KEY=your_key uv run python -m memory_hub.transport.mcp.mcp_server
```

---

## REST API

### Authentication

All endpoints (except `GET /api/v1/health`) require:

```
X-API-Key: <your-agent-api-key>
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/memory` | Store a memory |
| `POST` | `/api/v1/memory/search` | Semantic search |
| `POST` | `/api/v1/memory/batch` | Bulk store memories |
| `GET` | `/api/v1/memory/export` | Export all memories for a project |
| `GET` | `/api/v1/health` | Health check (public) |
| `GET` | `/api/v1/agents` | List registered agents |

### Store a Memory

```bash
curl -X POST http://localhost:8000/api/v1/memory \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "The brand voice should be conversational and friendly.",
    "project": "content-creation",
    "agent_id": "writer_agent",
    "category": "brand"
  }'
```

Response:
```json
{"memory_id": "abc123", "status": "ok"}
```

### Search Memories

```bash
curl -X POST http://localhost:8000/api/v1/memory/search \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "brand voice guidelines",
    "project": "content-creation",
    "limit": 5
  }'
```

Response:
```json
{
  "results": [
    {
      "id": "abc123",
      "content": "The brand voice should be conversational and friendly.",
      "project": "content-creation",
      "agent_id": "writer_agent",
      "score": 0.92,
      "category": "brand"
    }
  ],
  "query": "brand voice guidelines",
  "total": 1
}
```

### Memory Categories

`trend` | `brand` | `campaign` | `audience` | `career` | `task` | `code` | `general`

---

## MCP Server

### Claude Code

Add to `.claude/settings.json` (project) or `~/.claude/settings.json` (global):

```json
{
  "mcpServers": {
    "memory-hub": {
      "command": "uv",
      "args": [
        "run",
        "--project", "/path/to/cognee-mcp",
        "python", "-m", "memory_hub.transport.mcp.mcp_server"
      ],
      "env": {
        "AGENT_KEY": "your_claude_code_agent_key",
        "AGENT_ID": "claude_code_agent"
      }
    }
  }
}
```

See `config/mcp/claude_code.json` for the full template.

### OpenCode

See `config/mcp/opencode.json` for the OpenCode MCP config template.

### Antigravity IDE

See `config/mcp/antigravity.json` for the Antigravity config template.

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `memory_add` | Store a memory. Args: `content` (required), `category` (optional) |
| `memory_search` | Semantic search. Args: `query` (required), `limit` (default 10) |
| `memory_status` | Report agent identity, project, and memory count |

---

## Framework Adapters

All adapters communicate with the REST API via HTTP (no framework packages required to install this repo).

### LangChain

```python
from adapters.langchain_tool import MemoryAddTool, MemorySearchTool

COMMON = dict(
    project="content-creation",
    agent_id="research_agent",
    api_key="lc_research_a8f3k2m1",
)
tools = [MemoryAddTool(**COMMON), MemorySearchTool(**COMMON)]
# Pass to initialize_agent / create_react_agent as usual
```

### CrewAI

```python
from adapters.crewai_tool import MemoryHubTool
from crewai import Agent

memory = MemoryHubTool(
    project="content-creation",
    agent_id="writer_agent",
    api_key="crew_writer_xxx",
)
agent = Agent(role="Writer", tools=[memory], ...)
```

### AutoGen

```python
from adapters.autogen_tool import MemoryHubFunctions

hub = MemoryHubFunctions(
    project="dev-tools",
    agent_id="claude_code_agent",
    api_key="ag_claude_xxx",
)

# Register with ConversableAgent
assistant.register_function(function_map=hub.function_map)

# Or pass schemas to llm_config
llm_config = {"functions": hub.function_schemas, ...}
```

---

## Agent Registry

Agents are defined in `config/agents.yaml`. Each agent has:

- `name` — display name
- `framework` — `langchain` | `crewai` | `autogen` | `mcp`
- `project` — memory namespace (cross-project reads blocked)
- `role` — agent role description
- `permissions.read_shared` / `write_shared` — access control flags

API keys are **not** stored in the YAML. Set them in `.env`:

```env
AGENT_KEYS={"lc_research_a8f3k2m1": "research_agent", "crew_writer_xxx": "writer_agent"}
```

The hub master key (`HUB_API_KEY`) has access to all endpoints.

---

## Architecture

```
memory_hub/
  config.py              # Pydantic Settings — loads .env + agents.yaml
  app.py                 # FastAPI app factory (create_app)
  interfaces/            # Protocol definitions (MemoryStore, AgentRegistry, HealthCheck)
  models/                # Pydantic domain models, request/response schemas
  services/              # Business logic (MemoryService, RegistryService, HealthService)
  adapters/              # mem0 adapter (Gemini Embedding 2 backend)
  middleware/            # AuthMiddleware (X-API-Key validation)
  transport/
    rest/                # FastAPI routes + dependency injection
    mcp/                 # FastMCP server (memory_add, memory_search, memory_status)

adapters/                # Framework adapters (LangChain, CrewAI, AutoGen)
config/
  agents.yaml            # Agent registry (no secrets)
  mcp/                   # MCP server configs for each IDE/CLI tool
tests/
  unit/                  # 120+ unit tests (mock I/O)
  integration/           # Integration tests (TestClient)
```

### Project Scoping

Every memory write and search is scoped to a **project**:

- REST API: `project` field in request body (validated against authenticated agent)
- MCP Server: `project` is locked at startup from the agent's registry entry — callers cannot override
- Adapters: `project` is set in the constructor — not passed per-call

This prevents cross-project data leakage.

---

## Development

### Run Tests

```bash
uv run pytest                          # all tests
uv run pytest --cov=memory_hub         # with coverage
uv run pytest tests/unit/              # unit tests only
uv run pytest tests/integration/       # integration tests only
```

### Lint & Type Check

```bash
uv run ruff check src/ tests/ adapters/
uv run mypy src/
```

### Project Structure (src layout)

The package is installed in editable mode via hatchling. Import as:

```python
from memory_hub.app import create_app
from memory_hub.services.memory_service import MemoryService
```

---

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Google AI API key for Gemini Embedding 2 |
| `HUB_API_KEY` | Yes | — | Master API key (full access) |
| `AGENT_KEYS` | No | `{}` | JSON map of `api_key` → `agent_id` |
| `AGENTS_YAML_PATH` | No | `config/agents.yaml` | Path to agents config |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server port |
| `LOG_LEVEL` | No | `INFO` | Logging level |

---

## License

MIT
