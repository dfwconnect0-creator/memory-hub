# Memory Hub v5 — Troubleshooting Guide

Common issues encountered during build and their fixes.

---

## Startup Errors

### "Unsupported embedding provider: google"

**Error:**
```
Value error, Unsupported embedding provider: google
```

**Cause:** mem0ai uses `"gemini"` as the provider name, not `"google"`.

**Fix** in `src/memory_hub/adapters/mem0_adapter.py`:
```python
# WRONG
"embedder": {"provider": "google", ...}

# CORRECT
"embedder": {"provider": "gemini", ...}
```

---

### "The api_key client option must be set... OPENAI_API_KEY"

**Error:**
```
openai.OpenAIError: The api_key client option must be set either by passing
api_key to the client or by setting the OPENAI_API_KEY environment variable
```

**Cause:** mem0 needs BOTH an embedder AND an LLM. Without explicit LLM config, it defaults to OpenAI.

**Fix** — Add LLM config pointing to Gemini:
```python
def _build_mem0_config(settings):
    return {
        "llm": {                          # THIS WAS MISSING
            "provider": "gemini",
            "config": {
                "model": "gemini-2.0-flash",
                "api_key": settings.GEMINI_API_KEY,
            },
        },
        "embedder": {
            "provider": "gemini",
            "config": {
                "model": "gemini-embedding-002",
                "embedding_dims": 768,
                "api_key": settings.GEMINI_API_KEY,
            },
        },
        ...
    }
```

---

## Install / Dependency Issues

### "zsh: no matches found: uvicorn[standard]"

**Cause:** zsh interprets `[standard]` as a glob pattern.

**Fix:** Quote it:
```bash
uv add 'uvicorn[standard]'
```

---

### "zsh: command not found: #"

**Cause:** Pasting multi-line commands with inline `#` comments. zsh treats `#` differently when pasted in certain modes.

**Fix:** Run commands without inline comments, or paste them one at a time.

---

### "ModuleNotFoundError: No module named 'mem0ai'"

**Cause:** The PyPI package is `mem0ai` but the Python import is `mem0`.

**Fix:**
```python
# WRONG
import mem0ai

# CORRECT
from mem0 import Memory
```

---

### "ModuleNotFoundError: No module named 'fastapi'"

**Cause:** `uv add fastapi uvicorn[standard] ...` failed silently because `[standard]` broke the entire command. So fastapi never got installed.

**Fix:** Re-run missing deps separately:
```bash
uv add fastapi pydantic pydantic-settings
```

---

## Claude CLI Issues

### "Command contains quoted characters in flag names"

**Cause:** Claude CLI security warning when pasting multi-line prompts with `#` characters.

**Fix:** Write prompts as single paragraphs, no newlines, no `#`:
```
Execute Phase 4 from plans/multi_agent_memory_plan_v5.md. Build the MCP server using the mcp SDK. Define tools: memory_add, memory_search, memory_status. Write tests first then implement.
```

---

## Runtime Notes

### 403 on localhost:8000/

**Not a bug.** The auth middleware blocks all paths except `/health` and `/api/v1/health`. Visiting `http://localhost:8000/` in a browser triggers a 403 because there's no `X-API-Key` header. This is correct behavior.

### Running commands from wrong directory

The `uv run` command must be executed from `~/cognee-mcp` (where `pyproject.toml` lives). Running from any other directory will fail with module import errors.

```bash
# Always cd first
cd ~/cognee-mcp && uv run uvicorn memory_hub.app:create_app --factory --port 8000
```
