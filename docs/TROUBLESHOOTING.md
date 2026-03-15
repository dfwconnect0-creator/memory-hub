# Memory Hub v5 — Troubleshooting Guide
> Last updated: 2026-03-15 | Version: v5.0.0

Common issues encountered during development and deployment, with causes and verified fixes.

---

## Table of Contents
- [Startup Errors](#startup-errors)
- [Dependency Issues](#dependency-issues)
- [API Errors](#api-errors)
- [CLI Agent Issues](#cli-agent-issues)
- [Environment Issues](#environment-issues)

---

## Startup Errors

### TSG-001: "Unsupported embedding provider: google"

**Symptom:**
```
Value error, Unsupported embedding provider: google
ERROR: Application startup failed.
```

**Cause:** mem0ai uses `"gemini"` as the provider name, not `"google"`.

**Fix:** In `src/memory_hub/adapters/mem0_adapter.py`:
```python
# ❌ WRONG
"embedder": {"provider": "google", ...}

# ✅ CORRECT
"embedder": {"provider": "gemini", ...}
```

**Status:** Fixed in commit `0a604b9` (2026-03-15)

---

### TSG-002: "The api_key client option must be set... OPENAI_API_KEY"

**Symptom:**
```
openai.OpenAIError: The api_key client option must be set either by passing
api_key to the client or by setting the OPENAI_API_KEY environment variable
```

**Cause:** mem0 requires BOTH an embedder AND an LLM config. Without explicit LLM config, it defaults to OpenAI which requires `OPENAI_API_KEY`.

**Fix:** Add LLM config pointing to Gemini in `_build_mem0_config()`:
```python
"llm": {
    "provider": "gemini",
    "config": {
        "model": "gemini-2.5-flash",
        "api_key": settings.GEMINI_API_KEY,
    },
},
```

**Status:** Fixed in commit `0a604b9` (2026-03-15)

---

### TSG-003: "models/gemini-2.0-flash is no longer available"

**Symptom:**
```
google.genai.errors.ClientError: 404 NOT_FOUND.
'This model models/gemini-2.0-flash is no longer available to new users.'
```

**Cause:** `gemini-2.0-flash` was deprecated. Must use current model.

**Fix:** Update model name in `_build_mem0_config()`:
```python
# ❌ Deprecated
"model": "gemini-2.0-flash"

# ✅ Current (as of March 2026)
"model": "gemini-2.5-flash"
```

**Status:** Fixed in commit `0a604b9` (2026-03-15)

---

### TSG-004: "models/gemini-embedding-002 is not found"

**Symptom:**
```
google.genai.errors.ClientError: 404 NOT_FOUND.
'models/gemini-embedding-002 is not found for API version v1beta'
```

**Cause:** The API model name is `gemini-embedding-001` (stable) or `gemini-embedding-exp-03-07` (preview). `gemini-embedding-002` does not exist yet in the API.

**Fix:** Use the correct model name:
```python
# ❌ Does not exist
"model": "gemini-embedding-002"

# ✅ Stable, available
"model": "gemini-embedding-001"
```

**Reference:** [Gemini Embedding Models](https://ai.google.dev/gemini-api/docs/models#embedding)

**Status:** Fixed in commit `0a604b9` (2026-03-15)

---

### TSG-005: "address already in use" (port 8000)

**Symptom:**
```
ERROR: [Errno 48] error while attempting to bind on address ('127.0.0.1', 8000): address already in use
```

**Cause:** A previous server instance is still running on port 8000.

**Fix:**
```bash
kill $(lsof -ti:8000) 2>/dev/null; sleep 1; cd ~/cognee-mcp && uv run uvicorn memory_hub.app:create_app --factory --port 8000
```

---

## Dependency Issues

### TSG-006: "zsh: no matches found: uvicorn[standard]"

**Cause:** zsh interprets `[standard]` as a glob pattern.

**Fix:** Quote the package name:
```bash
uv add 'uvicorn[standard]'
```

---

### TSG-007: "ModuleNotFoundError: No module named 'mem0ai'"

**Cause:** The PyPI package is `mem0ai` but the Python import name is `mem0`.

**Fix:**
```python
# ❌ WRONG
import mem0ai

# ✅ CORRECT
from mem0 import Memory
```

---

### TSG-008: "ModuleNotFoundError: No module named 'fastapi'"

**Cause:** When `uv add fastapi uvicorn[standard] ...` fails due to the glob issue (TSG-006), ALL packages in that command are skipped — including fastapi.

**Fix:** Install missing deps separately:
```bash
uv add fastapi pydantic pydantic-settings
```

---

### TSG-009: "zsh: command not found: #"

**Cause:** Pasting multi-line shell commands with inline `#` comments. zsh treats `#` differently when pasted in certain terminal modes.

**Fix:** Run commands without inline comments, or paste them one at a time.

---

## API Errors

### TSG-010: "Invalid API key" (403)

**Symptom:**
```json
{"message": "Invalid API key", "code": "INVALID_AUTH"}
```

**Cause 1:** The server was started before `.env` was updated. Config is loaded at startup and cached in memory.

**Fix:** Restart the server after changing `.env`:
```bash
kill $(lsof -ti:8000) 2>/dev/null; sleep 1; cd ~/cognee-mcp && uv run uvicorn memory_hub.app:create_app --factory --port 8000
```

**Cause 2:** The `X-API-Key` header value doesn't match `HUB_API_KEY` or any key in `AGENT_KEYS`.

**Fix:** Check your `.env` file:
```bash
grep HUB_API_KEY ~/cognee-mcp/.env
```

---

### TSG-011: 403 on localhost:8000/ (browser)

**Not a bug.** The auth middleware blocks all paths except `/health` and `/api/v1/health`. Visiting `http://localhost:8000/` in a browser triggers a 403 because there's no `X-API-Key` header. This is correct behavior.

---

### TSG-012: "Internal Server Error" (500) with no details in response

**Cause:** The route handlers don't have try/catch blocks (by design — FastAPI returns 500 for unhandled exceptions).

**Fix:** Check the **server terminal** (where uvicorn is running) for the full Python traceback. The client only sees "Internal Server Error".

---

## CLI Agent Issues

### TSG-013: Claude CLI "Command contains quoted characters" warning

**Symptom:**
```
Command contains a quoted newline followed by a #-prefixed line,
which can hide arguments from line-based permission
```

**Cause:** Claude CLI's security check flags multi-line commands with `#` characters.

**Fix:** Write prompts as single paragraphs with no newlines and no `#`:
```
Execute Phase 4 from plans/multi_agent_memory_plan_v5.md. Build the MCP server using the mcp SDK. Define tools: memory_add, memory_search, memory_status. Write tests first then implement.
```

---

## Environment Issues

### TSG-014: Commands fail when run from wrong directory

**Cause:** `uv run` must be executed from the directory containing `pyproject.toml`.

**Fix:** Always prefix with `cd`:
```bash
cd ~/cognee-mcp && uv run uvicorn memory_hub.app:create_app --factory --port 8000
```

---

### TSG-015: .env committed to git with real API keys

**Cause:** `.env` was not in `.gitignore` during initial bootstrap.

**Fix:** Remove from git history and add to `.gitignore`:
```bash
cd ~/cognee-mcp && git rm --cached .env && git commit -m "sec: remove .env from tracking"
```

**Prevention:** `.gitignore` now includes `.env` (added 2026-03-15).
