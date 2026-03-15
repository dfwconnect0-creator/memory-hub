# Memory Hub v5 — Quick Start Guide
> Last updated: 2026-03-15 | Version: v5.0.0

Get your Memory Hub running in under 5 minutes.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Gemini API key (free) from https://aistudio.google.com/apikey

---

## 1. Clone and Install

```bash
cd ~/cognee-mcp
uv sync
```

## 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set:
```env
GEMINI_API_KEY=your-real-gemini-api-key
HUB_API_KEY=your-secret-hub-key
```

To generate a secure hub key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 3. Start the Server

```bash
cd ~/cognee-mcp && uv run uvicorn memory_hub.app:create_app --factory --port 8000
```

## 4. Verify It Works

**Health check (no auth):**
```bash
curl http://localhost:8000/api/v1/health
```

**Store a memory (auth required):**
```bash
curl -X POST http://localhost:8000/api/v1/memory \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_HUB_API_KEY" \
  -d '{"content":"Hello from Memory Hub!","project":"dev-tools","agent_id":"antigravity_agent","category":"general"}'
```

**Search memories:**
```bash
curl -X POST http://localhost:8000/api/v1/memory/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_HUB_API_KEY" \
  -d '{"query":"Hello","project":"dev-tools"}'
```

---

## 5. Connect CLI Agents

### Claude Code

Add to `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "memory-hub": {
      "command": "uv",
      "args": ["run", "--project", "/Users/mohamedsalah/cognee-mcp", "python", "-m", "memory_hub.transport.mcp.mcp_server"],
      "env": {
        "AGENT_KEY": "YOUR_HUB_API_KEY",
        "AGENT_ID": "claude_code_agent"
      }
    }
  }
}
```

### OpenCode

Copy `config/mcp/opencode.json` to OpenCode's MCP configuration directory.

### Antigravity

Copy `config/mcp/antigravity.json` to Antigravity's MCP configuration directory.

---

## 6. Run Tests

```bash
cd ~/cognee-mcp && uv run pytest
```

With coverage:
```bash
cd ~/cognee-mcp && uv run pytest --cov=memory_hub --cov-report=term-missing
```

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|:---|:---|:---|:---|
| `/api/v1/health` | GET | ❌ | Health check |
| `/api/v1/memory` | POST | ✅ | Add a memory |
| `/api/v1/memory/search` | POST | ✅ | Search memories |
| `/api/v1/memory/batch` | POST | ✅ | Batch add memories |
| `/api/v1/memory/export` | GET | ✅ | Export project memories |
| `/api/v1/agents` | GET | ✅ | List registered agents |

---

## Common Issues

See [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) for solutions to common problems.
