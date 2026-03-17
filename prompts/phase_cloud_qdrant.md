# Cloud Qdrant Migration — Claude CLI Prompt

**Date:** 2026-03-17 | **Repo:** `~/cognee-mcp/`
**Goal:** Replace local Qdrant file storage with Qdrant Cloud so both Mac and Ubuntu share the same memory.

---

## Critical Warnings

| Warning | Fix |
|:---|:---|
| W1: dotenv crash | `.env` must be loaded before Settings() — already handled by pydantic_settings |
| W2: Never `git add -A` | Stage specific files only, grep for secrets before commit |
| W3: Don't break local mode | Keep local path as fallback when QDRANT_URL is empty |
| W4: UV cache | Use `UV_CACHE_DIR=/tmp/uv-cache` prefix if cache errors |
| W5: Mac permissions | The old `~/.mem0/qdrant_data` path has macOS SIP permission locks — that's WHY we're moving to cloud |

---

## The Prompt

```
Read these two files first: ~/cognee-mcp/src/memory_hub/config.py and ~/cognee-mcp/src/memory_hub/adapters/mem0_adapter.py. You are adding Qdrant Cloud support so that two machines (Mac + Ubuntu) share the same vector database over the internet instead of using local file storage. This is a small, focused change — only 2 files need to be modified, nothing else.

STEP 1 — Modify ~/cognee-mcp/src/memory_hub/config.py: Add two new optional fields to the Settings class, after the LOG_LEVEL field: QDRANT_URL with type str and default "" (empty string means use local storage), and QDRANT_API_KEY with type str and default "" (empty string). Add a comment above each: "# Qdrant Cloud URL — set to enable cross-machine memory sync" and "# Qdrant Cloud API key". Do NOT change any existing fields. Do NOT remove anything.

STEP 2 — Modify ~/cognee-mcp/src/memory_hub/adapters/mem0_adapter.py: In the _build_mem0_config function, change the "vector_store" config block to support BOTH cloud and local modes. If settings.QDRANT_URL is a non-empty string, use cloud mode with "url" and "api_key" keys. If settings.QDRANT_URL is empty, fall back to local path mode with "path" key pointing to "/tmp/mem0_storage/qdrant_data". The exact code should be:

```python
    qdrant_config: dict[str, Any] = {
        "collection_name": "memory_hub",
        "embedding_model_dims": 3072,
    }
    if settings.QDRANT_URL:
        qdrant_config["url"] = settings.QDRANT_URL
        qdrant_config["api_key"] = settings.QDRANT_API_KEY
        logger.info("Qdrant: using cloud at %s", settings.QDRANT_URL)
    else:
        qdrant_config["path"] = "/tmp/mem0_storage/qdrant_data"
        logger.info("Qdrant: using local storage at /tmp/mem0_storage/qdrant_data")
```

Replace the entire existing "vector_store" block with this. The rest of _build_mem0_config (llm and embedder sections) stays exactly the same — do NOT touch them.

STEP 3 — Verify: Run "UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/memory_hub/config.py src/memory_hub/adapters/mem0_adapter.py" and fix any lint errors. Then run "UV_CACHE_DIR=/tmp/uv-cache uv run python -c 'from memory_hub.config import Settings; s = Settings(); print(f\"QDRANT_URL={s.QDRANT_URL!r}\"); print(f\"QDRANT_API_KEY={s.QDRANT_API_KEY!r}\")'" to verify the new fields load correctly (they should print empty strings since .env doesn't have them yet).

STEP 4 — Add the new env vars to .env as comments (NOT active values — the user will fill in their Qdrant Cloud credentials): Add these lines at the end of ~/cognee-mcp/.env:

```
# ── Optional: Cloud Vector DB ─────────────────────────────────────
# Set both to enable cross-machine memory sync via Qdrant Cloud
# Get free cluster at: https://cloud.qdrant.io
# QDRANT_URL=https://your-cluster-id.us-east-1-0.aws.cloud.qdrant.io:6333
# QDRANT_API_KEY=your_qdrant_cloud_api_key
```

STEP 5 — Git: Stage ONLY the changed files: "git add src/memory_hub/config.py src/memory_hub/adapters/mem0_adapter.py .env". Run "git diff --cached --name-only | grep -E '\.env|\.key|\.pem|secret|password'" — the .env will show up, which is expected since we're adding commented-out template lines, NOT real keys. Verify with "git diff --cached -- .env" that only the commented template lines were added and no real API keys are exposed. Then commit: "git commit -m 'feat(memory): add Qdrant Cloud support for cross-machine sync'".

That's it. Only config.py and mem0_adapter.py change. Do NOT modify any other files. Do NOT create new files. Do NOT add new dependencies.
```

---

## Validation After Running

```bash
# 1. Check it still works in local mode (no QDRANT_URL set)
cd ~/cognee-mcp && UV_CACHE_DIR=/tmp/uv-cache uv run uvicorn src.memory_hub.app:create_app --factory --port 8000

# 2. Check cloud mode (after user adds real Qdrant Cloud creds to .env)
# Server should log: "Qdrant: using cloud at https://..."

# 3. Test store + search
curl -X POST http://localhost:8000/api/v1/memory \
  -H "X-API-Key: cc_career_a7f2k9m3" \
  -H "Content-Type: application/json" \
  -d '{"content":"Cloud sync test from Mac","category":"general"}'

curl "http://localhost:8000/api/v1/memory/search?query=cloud+sync&limit=3" \
  -H "X-API-Key: cc_career_a7f2k9m3"
```
