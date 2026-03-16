# Memory Hub — Debugging & Lessons Learned Guide

> **Audience:** Planning Agent, Reviewer Agent, Debugging Agent, Claude CLI
>
> This document captures hard-won debugging lessons from building the Career Coach and Content Researcher agents. **Read this before writing or reviewing any agent code.**

---

## 🔴 Critical: Issues That Will Silently Break Everything

### 1. Embedding Dimension Mismatch (Silent Data Loss)

**What happens:** Store returns `{"memory_id":"","status":"ok"}` — looks successful but nothing is actually stored. Search returns empty forever.

**Root cause:** `gemini-embedding-001` returns **3072** dimensions, not 768. If the Qdrant collection was created with 768 dims, all inserts silently fail.

**How to detect:**
- `memory_id` is empty string `""` in API response
- `mem0.add()` returns `{'results': []}`
- No errors in logs — completely silent

**Fix:** Ensure ALL dimension configs match:
```python
# mem0_adapter.py — BOTH must be 3072
"embedder": {"config": {"embedding_dims": 3072}},
"vector_store": {"config": {"embedding_model_dims": 3072}},
```

**After fixing:** You MUST delete `~/.mem0` and restart the server. Qdrant caches the old collection schema.

```bash
kill $(lsof -ti:8000); rm -rf ~/.mem0; sleep 2; uv run uvicorn ...
```

> [!CAUTION]
> If you ever change the embedding model, you MUST:
> 1. Check the new model's output dimensions
> 2. Update BOTH `embedding_dims` and `embedding_model_dims`
> 3. Delete `~/.mem0` (old collection has wrong dims)
> 4. Restart the server

---

### 2. mem0 Fact Extraction Rejects "Non-Personal" Content

**What happens:** `mem0.add()` returns `{'results': []}` for perfectly valid content.

**Root cause:** mem0 uses the LLM internally to extract "personal facts" before storing. Generic or tagged content like `[TREND] AI is growing` gets rejected because it doesn't look like a fact about a person.

**How to detect:**
- Add debug print: `print(f"mem0.add result: {result}")`
- If `results` is empty list, mem0's LLM rejected the content

**Fix:** Wrap content with personal framing:
```python
# BAD — mem0 rejects this
content = "[TREND] AI is becoming dominant in 2026"

# GOOD — mem0 stores this
content = "User researched and found: [TREND] AI is becoming dominant in 2026"
```

> [!IMPORTANT]
> mem0 is designed for PERSONAL memory ("user likes Python", "user wants to be an engineer"). Research data, logs, and generic facts need a personal wrapper or they get silently dropped.

---

### 3. `contextlib.suppress(Exception)` Hides Everything

**What happens:** Code runs, no errors shown, but nothing works.

**Root cause:** `contextlib.suppress(Exception)` catches ALL errors including 403s, 422s, timeouts — completely silently.

**Rule:** During development, NEVER use `contextlib.suppress`. Use try/except with logging:
```python
# ❌ BAD — hides all errors
with contextlib.suppress(Exception):
    self.store_finding(line)

# ✅ GOOD — shows what's wrong
try:
    self.store_finding(line)
except Exception as e:
    print(f"⚠ store failed: {e}")
```

Only switch to `contextlib.suppress` AFTER the feature is fully tested and working.

---

## 🟡 Important: Issues That Cause Confusing Failures

### 4. `.env` Not Loaded in CLI Agents

**What happens:** Agent gets 403 Forbidden from Memory Hub.

**Root cause:** Python CLIs don't automatically load `.env`. If `CAREER_COACH_API_KEY` or `CONTENT_RESEARCHER_API_KEY` isn't in the shell environment, the agent sends an empty API key.

**Fix:** Every CLI module MUST have a `_load_env()` function called BEFORE any imports that use env vars:
```python
def _load_env(path):
    """Minimal .env loader — no external deps."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

# Call BEFORE other imports
_load_env(Path(__file__).resolve().parents[2] / ".env")
```

### 5. AGENT_KEYS Must Include Every Agent

**What happens:** New agent gets 403 even though it has an API key.

**Root cause:** The `.env` file has `AGENT_KEYS` as a JSON map. If a new agent's key isn't in this map, the auth middleware rejects it.

**Checklist for adding a new agent:**
```bash
# .env — add BOTH lines:
NEW_AGENT_API_KEY=na_agent_xxxxxxxx
AGENT_KEYS={"cc_career_a7f2k9m3": "career_coach_agent", "na_agent_xxxxxxxx": "new_agent_id"}
```

### 6. MemoryCategory Enum Validation (422 Errors)

**What happens:** `422 Unprocessable Entity` when storing a memory.

**Root cause:** The `category` field validates against the `MemoryCategory` enum. Only these values are valid:
```
trend, brand, campaign, audience, career, task, code, general
```

Sending `"insight"` or `"source"` as a category → 422 rejection.

**Fix:** Map unsupported categories to valid ones, or add new values to the enum.

### 7. `~/.mem0` Permission Lock (macOS)

**What happens:** Server fails to start with `PermissionError: Operation not permitted: '.mem0/migrations_qdrant'`

**Root cause:** Qdrant's local storage in `~/.mem0` gets locked by macOS extended attributes. A running server also locks the directory.

**Fix:**
```bash
# Kill the server FIRST, then clean
kill $(lsof -ti:8000) 2>/dev/null
xattr -rc ~/.mem0
rm -rf ~/.mem0
# Now restart
uv run uvicorn memory_hub.app:create_app --factory --port 8000
```

### 8. `uv` Cache Permission Issues

**What happens:** `uv run` fails with `failed to open file .cache/uv/sdists-v9/.git: Operation not permitted`

**Fix:** Use `UV_CACHE_DIR=/tmp/uv-cache` prefix:
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python -m agents.content_researcher.cli --topic "test"
```

---

## 🟢 Best Practices for Agent Development

### Testing Checklist (Run Before Every Commit)
```bash
# 1. Lint
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check agents/ tests/ src/

# 2. Tests
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v --tb=short

# 3. Secret scan
git diff --cached -- '*.env*' '*.key' '*.pem'

# 4. Live integration test (requires running server)
curl -s http://localhost:8000/api/v1/health
```

### Git Safety
- **NEVER commit `.env`** — only `.env.example` with placeholder values
- **Always run secret scan** before committing
- **Use conventional commits:** `feat(agent):`, `fix:`, `docs:`

### Server Restart Protocol
When changing `mem0_adapter.py`, `.env`, or any server config:
```bash
kill $(lsof -ti:8000) 2>/dev/null
xattr -rc ~/.mem0 2>/dev/null
rm -rf ~/.mem0              # Only if changing embedding dims or Qdrant schema
sleep 2
cd ~/cognee-mcp && uv run uvicorn memory_hub.app:create_app --factory --port 8000
```

### Debug Logging Pattern
When something fails silently, add temporary debug prints:
```python
result = mem0_operation()
print(f"[DEBUG] result: {result}", flush=True)  # flush=True for uvicorn
```
Remove debug prints before committing.

---

## Quick Reference: Error → Cause → Fix

| Error | Cause | Fix |
|:------|:------|:----|
| `memory_id: ""` | Dimension mismatch OR mem0 fact rejection | Check dims (3072), wrap content |
| `403 Forbidden` | Missing/wrong API key | Check `.env` loading + `AGENT_KEYS` |
| `422 Unprocessable` | Invalid category enum value | Use valid `MemoryCategory` values |
| `results: []` from mem0 | Content rejected by fact extraction | Add "User researched:" prefix |
| `PermissionError .mem0` | macOS extended attrs lock | `xattr -rc ~/.mem0 && rm -rf ~/.mem0` |
| `uv` cache error | Git lock in uv cache | `UV_CACHE_DIR=/tmp/uv-cache` |
| `timed out` on store | mem0 LLM call took too long | Retry, or check Gemini API quota |
| Echo responses only | No LLM integration in chat() | Add `genai.Client` + `generate_content` |
