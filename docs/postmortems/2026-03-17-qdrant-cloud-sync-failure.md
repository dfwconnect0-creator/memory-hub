# Post-Mortem: Qdrant Cloud Sync Not Working
**Date:** 2026-03-17
**Severity:** High — cross-device memory sync completely broken
**Status:** Resolved
**Reported by:** Manual testing (Claude Code + user)
**Affected component:** `mem0_adapter.py` → Qdrant Cloud write path

---

## Summary

Memories written to `career_coach_agent` were not persisting to Qdrant Cloud. The service returned `201 Created` on every write, making the failure completely invisible. On another device (or after a server restart), all memories were gone. Two root causes were found and fixed in sequence.

---

## Timeline

| Time | Event |
|------|-------|
| ~15:00 | User reports cross-device memory not working |
| 15:10 | Health check passes — server appears healthy |
| 15:15 | Direct Qdrant Cloud API test confirms connection works (without `:6333`) |
| 15:20 | `.env` identified with wrong URL — `:6333` removed |
| 15:25 | Server restarted — writes still fail, `points_count` unchanged |
| 15:30 | Server log reveals `PointStruct vector=None` Pydantic errors |
| 15:40 | mem0 v1.0.5 source traced — bug in `qdrant.py update()` confirmed |
| 15:45 | Patch applied to venv — writes confirmed landing in Qdrant Cloud |

---

## Root Cause 1 — Wrong Qdrant URL (`:6333`)

### What happened
The `QDRANT_URL` in `.env` included port `:6333`:
```
QDRANT_URL=https://xxxx.eu-west-1-0.aws.cloud.qdrant.io:6333
```

Port `6333` is the default port for **self-hosted Qdrant running locally**. Qdrant Cloud listens on standard HTTPS port `443`. The extra port caused connections to fail or be ignored silently — mem0 did not raise an exception.

### Why it was silent
mem0 wraps all Qdrant operations in broad `try/except` blocks. Connection failures at the URL level are swallowed. The API still returned `201 Created` because the response is built before the Qdrant write completes (fire-and-forget in `DualMemoryService`).

### Fix
Removed `:6333` from `.env`:
```env
# BEFORE (broken)
QDRANT_URL=https://xxxx.aws.cloud.qdrant.io:6333

# AFTER (correct)
QDRANT_URL=https://xxxx.aws.cloud.qdrant.io
```

### Prevention
Always verify a Qdrant URL before trusting it:
```bash
curl -s -H "api-key: $QDRANT_API_KEY" "$QDRANT_URL/collections"
# Must return {"status":"ok"} — if it hangs, the URL is wrong
```

---

## Root Cause 2 — mem0 v1.0.5 Bug: `event: NONE` Crashes Qdrant Update

### What happened
Even after the URL fix, writes still failed. Server logs showed:

```
Error processing memory action: {'id': '0', 'text': '...', 'event': 'NONE'},
Error: 6 validation errors for PointStruct
vector.list[float]
  Input should be a valid list [input_value=None, input_type=NoneType]
```

### How mem0 processes a write
1. Content is sent to Gemini LLM for **fact extraction**
2. Each extracted fact is assigned an event: `ADD`, `UPDATE`, `DELETE`, or `NONE`
3. `NONE` = "this fact is already known, no change needed"
4. `NONE` facts should be skipped — **but they weren't**

### The bug
In `mem0/vector_stores/qdrant.py`, the `update()` method:

```python
def update(self, vector_id, vector=None, payload=None):
    point = PointStruct(id=vector_id, vector=vector, payload=payload)
    self.client.upsert(...)  # crashes — PointStruct rejects vector=None
```

When the `NONE` branch in `main.py` calls `update(vector=None)` to refresh session metadata, the Qdrant store tries to build a `PointStruct` with `vector=None`. Pydantic rejects it with 6 validation errors (one per allowed vector type). The exception is caught by a surrounding `logger.error()` and swallowed — the API caller never knows.

### Why it looked like a duplicate issue
The same `memory_id: ""` symptom (empty ID on write) appears in three unrelated situations:
1. Embedding dimension mismatch (existing issue #1 in DEBUGGING_GUIDE)
2. mem0 LLM rejects content as non-personal (existing issue #2)
3. **This bug** — NONE event crashes before any ID can be returned

All three look identical from the outside. The only way to distinguish them is to check the server log.

### Fix
Patched `.venv/lib/python3.12/site-packages/mem0/vector_stores/qdrant.py`:

```python
def update(self, vector_id, vector=None, payload=None):
    if vector is None:
        # Only refresh payload — keep the existing embedding
        if payload:
            self.client.set_payload(
                collection_name=self.collection_name,
                payload=payload,
                points=[vector_id],
            )
    else:
        point = PointStruct(id=vector_id, vector=vector, payload=payload)
        self.client.upsert(collection_name=self.collection_name, points=[point])
```

> **Note:** This is a venv patch. It will be lost on `uv sync`. Check if mem0 > 1.0.5 fixes this before re-patching. See DEBUGGING_GUIDE.md issue #11 for the full tracking entry.

---

## What Worked Well

- **DualMemoryService architecture** held up — Cognee continued serving search results even while mem0 was broken. The system degraded gracefully.
- **Health endpoint** correctly reported 9 registered agents throughout — good signal that registry is independent of storage.
- **Direct Qdrant API test** (`curl $QDRANT_URL/collections`) was the fastest way to isolate whether the problem was in the URL or in mem0.

---

## What Went Wrong (Process)

| Bad Practice | Better Practice |
|---|---|
| `:6333` added to cloud URL — not validated at startup | Add a Qdrant connectivity check to the health endpoint |
| mem0 write errors fully swallowed by `logger.error` | Surface storage errors as a degraded health status |
| `201 Created` returned even when Qdrant write failed | Write response should reflect actual storage success |
| No cross-device smoke test in CI | Add a test that writes a memory and reads it back via the actual Qdrant URL |
| venv patch required for a third-party library bug | Pin to a fixed mem0 version or fork; track in `pyproject.toml` comments |

---

## Action Items

| Priority | Item | Owner |
|----------|------|-------|
| High | Add Qdrant Cloud connectivity check to `/health` endpoint | Dev |
| High | Track mem0 releases — remove venv patch when upstream fixes it | Dev |
| Medium | Return a storage error (not `201`) when mem0 write returns `results: []` | Dev |
| Medium | Add integration smoke test: write → wait 5s → search → assert result found | Dev |
| Low | Document Qdrant URL format in `.env.example` with a comment | Dev |

---

## References

- `docs/DEBUGGING_GUIDE.md` — Issues #10 (wrong URL) and #11 (mem0 NONE bug)
- Patched file: `.venv/lib/python3.12/site-packages/mem0/vector_stores/qdrant.py`
- mem0 version at time of incident: `1.0.5`
- Qdrant Cloud docs: https://qdrant.tech/documentation/cloud/
