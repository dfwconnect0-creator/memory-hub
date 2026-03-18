# Memory Hub: Local-Primary + Cloud Backup — Claude CLI Prompts

**Date:** 2026-03-18 | **Role:** Planner (Antigravity) | **Builder:** Claude CLI
**Repo:** `~/cognee-mcp/`
**Goal:** Switch Memory Hub from cloud-only Qdrant to local-primary with nightly cloud backup + manual sync trigger.

---

## Critical Warnings

| Warning | Fix |
|:---|:---|
| W1: UV cache | `UV_CACHE_DIR=/tmp/uv-cache` prefix if cache errors |
| W2: Never `git add -A` | Stage specific files only, grep for secrets before commit |
| W3: Keep existing tests passing | Run full `uv run pytest tests/` after every phase |
| W4: Don't break MCP server | The MCP server must still start with `AGENT_ID` and `AGENT_KEY` env vars |
| W5: qdrant-client is a transitive dep | Already installed via mem0ai — do NOT add it to pyproject.toml |
| W6: Existing cloud data | The sync upserts, never deletes — cloud data is preserved |

---

## Current State

- `mem0_adapter.py` has local/cloud branching: uses cloud when `QDRANT_URL` is set, local `/tmp/` path when empty
- `.env` currently has `QDRANT_URL` and `QDRANT_API_KEY` active → hub runs in cloud-only mode
- Need to flip to: local is primary for reads/writes, cloud is backup-only target
- `DualMemoryService` pattern in `dual_memory_service.py` is a useful reference for async fire-and-forget

---

## Phase 1: Config + Local-Only Adapter (20 min)

```
Read ~/cognee-mcp/src/memory_hub/config.py and ~/cognee-mcp/src/memory_hub/adapters/mem0_adapter.py. You are switching the Memory Hub from cloud-only Qdrant to local-primary mode. The cloud credentials will still exist in .env but will only be used by a new sync service (Phase 2). Make these changes: In config.py, add these new fields to the Settings class after the QDRANT_API_KEY field: QDRANT_LOCAL_PATH with type str and default "memory-data/qdrant" with comment "# Local Qdrant storage path (persistent, not /tmp)", SYNC_ENABLED with type bool and default True with comment "# Enable nightly local-to-cloud backup", SYNC_SCHEDULE with type str and default "02:00" with comment "# Nightly backup time (HH:MM, 24h local time)". In mem0_adapter.py, modify the _build_qdrant_config function to ALWAYS use local mode. Remove the if/else branch that checks settings.QDRANT_URL. The function should now always return a config with "path" set to str(Path(settings.QDRANT_LOCAL_PATH).expanduser()) — import Path from pathlib at the top. Log "Qdrant: using local storage at {path}". Keep collection_name as "memory_hub" and embedding_model_dims as 3072. Do NOT modify .env yet. Write a test in tests/unit/test_config.py: add test_sync_settings_defaults that creates Settings with monkeypatched GEMINI_API_KEY and HUB_API_KEY, then asserts QDRANT_LOCAL_PATH == "memory-data/qdrant" and SYNC_ENABLED is True and SYNC_SCHEDULE == "02:00". Run "UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/test_config.py -v" then "UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/memory_hub/config.py src/memory_hub/adapters/mem0_adapter.py" to verify. Target: new test passes, all existing config tests pass, zero ruff errors.
```

## Phase 2: Sync Service (30 min)

```
Read ~/cognee-mcp/src/memory_hub/adapters/mem0_adapter.py and ~/cognee-mcp/src/memory_hub/config.py (modified in Phase 1). Now create the sync service that copies local Qdrant data to Qdrant Cloud. Create ~/cognee-mcp/src/memory_hub/services/sync_service.py with a SyncService class. The constructor takes a Settings object and stores it. It has an async method sync() that does: (1) import QdrantClient from qdrant_client at the top of the file, (2) create a local QdrantClient with path=str(Path(settings.QDRANT_LOCAL_PATH).expanduser()), (3) create a cloud QdrantClient with url=settings.QDRANT_URL and api_key=settings.QDRANT_API_KEY, (4) check if the local collection "memory_hub" exists using local_client.collection_exists("memory_hub"), if not return {"status": "skipped", "reason": "no local collection yet", "points_synced": 0}, (5) get collection info from local to know the point count, (6) scroll all points from local collection in batches of 100 using local_client.scroll(collection_name="memory_hub", limit=100, with_payload=True, with_vectors=True), (7) if cloud collection does not exist, recreate it using cloud_client.recreate_collection with same vector config (size=3072, distance=Cosine), (8) upsert each batch of points to cloud using cloud_client.upsert(collection_name="memory_hub", points=batch), (9) return {"status": "ok", "points_synced": total_count, "duration_seconds": round(elapsed, 2)}. Add proper error handling with try/except that returns {"status": "error", "message": str(e)}. Add logging throughout. Also add a method can_sync() -> bool that returns True only if settings.QDRANT_URL and settings.QDRANT_API_KEY are both non-empty. Write tests in ~/cognee-mcp/tests/unit/test_sync_service.py: test_can_sync_with_creds using monkeypatch to set QDRANT_URL and QDRANT_API_KEY then assert can_sync() is True, test_can_sync_without_creds with empty QDRANT_URL then assert can_sync() is False, test_sync_no_local_collection mocking QdrantClient to return collection_exists=False then assert result status is "skipped". Use unittest.mock.patch to mock QdrantClient. Run "UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/test_sync_service.py -v" then "UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/memory_hub/services/sync_service.py" to verify. Target: 3 tests pass, zero ruff errors.
```

## Phase 3: REST Endpoint + MCP Tool (25 min)

```
Read ~/cognee-mcp/src/memory_hub/services/sync_service.py (created in Phase 2), ~/cognee-mcp/src/memory_hub/transport/rest/memory_routes.py, and ~/cognee-mcp/src/memory_hub/transport/mcp/mcp_server.py. Add a manual sync trigger via both REST and MCP. In memory_routes.py, add a new POST /sync endpoint. It should get the sync_service from request.app.state.sync (will be wired in Phase 4), check if sync_service.can_sync() is True, if not return 400 with message "Cloud credentials not configured", otherwise call await sync_service.sync() and return the result dict. This endpoint should require the HUB_API_KEY (master key only, not agent keys). In mcp_server.py, add a new tool "memory_sync" with description "Trigger a manual backup of local memories to Qdrant Cloud. Returns sync report with points_synced count." The tool function should check if state has a sync_service attribute, if not return error "Sync not configured", then check can_sync(), then call sync() and return the JSON result. Also add "memory_sync_status" tool that returns {"sync_available": bool, "cloud_url": settings.QDRANT_URL or "not configured", "local_path": settings.QDRANT_LOCAL_PATH}. In the _production_lifespan function, after creating the memory_service, also create a SyncService(settings) and store it in the AgentState. Add sync_service field to the AgentState dataclass with type Any and default None. Write tests: in tests/unit/test_sync_routes.py, test POST /sync with mock sync_service that returns {"status": "ok", "points_synced": 5}, verify 200 response. Test POST /sync when can_sync is False, verify 400 response. Run "UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/test_sync_service.py tests/unit/test_sync_routes.py -v" then "UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/memory_hub/transport/" to verify. Target: 2 new route tests pass, all existing tests pass, zero ruff errors.
```

## Phase 4: Scheduler + App Wiring + .env Update (25 min)

```
Read ~/cognee-mcp/src/memory_hub/app.py and ~/cognee-mcp/src/memory_hub/services/sync_service.py. Now wire the sync scheduler into the app lifecycle and update .env. Create ~/cognee-mcp/src/memory_hub/services/sync_scheduler.py with async function start_sync_scheduler(sync_service, schedule_time_str, stop_event) that loops: calculates seconds until the next occurrence of schedule_time_str (parse "HH:MM" with datetime, if the time has passed today schedule for tomorrow), waits using asyncio.sleep in 60-second chunks checking stop_event.is_set() between sleeps (so shutdown is responsive), when the scheduled time arrives calls await sync_service.sync() and logs the result, then loops to calculate the next day. Use logging throughout. In app.py, modify the lifespan: after creating services, create SyncService(settings) and store in app.state.sync. If settings.SYNC_ENABLED and sync_service.can_sync(), create an asyncio.Event for stop_event and start the scheduler as a background task with asyncio.create_task(start_sync_scheduler(sync_service, settings.SYNC_SCHEDULE, stop_event)). In the yield cleanup section, set stop_event and cancel the scheduler task. Update ~/cognee-mcp/.env: reorganize the cloud section. Move QDRANT_URL and QDRANT_API_KEY under a new section header "# -- Cloud Backup (used by sync service, not primary storage) --". Add new entries: QDRANT_LOCAL_PATH=memory-data/qdrant, SYNC_ENABLED=true, SYNC_SCHEDULE=02:00. Keep all existing values unchanged. Update health_routes.py: extend the health response dict to include "storage_mode": "local", "sync_enabled": settings.SYNC_ENABLED, "last_sync": getattr(app.state, "last_sync_time", None). Write test_sync_scheduler.py: test that _seconds_until calculates correctly (extract it as a helper), mock datetime to return a known time, verify it calculates correct seconds to target. Run the full test suite "UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v" then "UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/ tests/" to check no regressions. Target: all tests pass, zero ruff errors. Git: stage with "git add src/memory_hub/config.py src/memory_hub/adapters/mem0_adapter.py src/memory_hub/services/sync_service.py src/memory_hub/services/sync_scheduler.py src/memory_hub/transport/rest/memory_routes.py src/memory_hub/transport/rest/health_routes.py src/memory_hub/transport/mcp/mcp_server.py src/memory_hub/app.py .env tests/unit/test_sync_service.py tests/unit/test_sync_routes.py tests/unit/test_sync_scheduler.py tests/unit/test_config.py". Run secrets check "git diff --cached --name-only | grep -E '\.env|\.key|\.pem|secret|password'" then verify with "git diff --cached -- .env" that no NEW secrets are exposed (existing ones were already in .env). Commit: "feat(sync): local-primary Qdrant with nightly cloud backup and manual sync trigger".
```

---

> **Run order:** Phase 1 → Phase 2 → Phase 3 → Phase 4. Come back to Antigravity for review + testing after each phase.

> **Total estimated time:** ~1.5 hours
