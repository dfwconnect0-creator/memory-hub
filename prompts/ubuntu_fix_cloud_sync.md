# Fix: Route Memory Through Qdrant Cloud (Not Cognee Local)

## The Problem

Memories are going to Cognee's local storage instead of the Memory Hub API → Qdrant Cloud.
The Mac can't see anything stored from Ubuntu because it's in a local Cognee DB, not the shared cloud.

## The Fix

### 1. Make sure `.env` has cloud Qdrant credentials

```bash
cd ~/cognee-mcp
# Check current state
grep QDRANT .env
```

If commented out or missing, add these to the END of `~/cognee-mcp/.env`:

```bash
MEM0_DIR=/tmp/mem0_storage
QDRANT_URL=https://7ea06f99-21fa-4c5e-a0aa-e39107c5f9f2.eu-west-1-0.aws.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.oQkXy1XQRUQfZiCrL47T10KlUn8np8OtB6o9UhKUY_s
```

### 2. Restart the Memory Hub server

```bash
kill $(lsof -ti:8000) 2>/dev/null; sleep 1
cd ~/cognee-mcp
MEM0_DIR=/tmp/mem0_storage uv run uvicorn src.memory_hub.app:create_app --factory --port 8000 &
```

### 3. Store via the Memory Hub API (NOT Cognee directly)

Use `curl` to POST to `localhost:8000`, NOT cognee MCP tools:

```bash
# Store a test memory
curl -s -X POST http://localhost:8000/api/v1/memory \
  -H "X-API-Key: cc_career_a7f2k9m3" \
  -H "Content-Type: application/json" \
  -d '{"content":"Melon said hello from Ubuntu! TrendCard belongs to the marketing-agent project.","category":"general","project":"bladina","agent_id":"career_coach_agent"}' | python3 -m json.tool

# Verify it's in cloud (search should return it)
curl -s -X POST http://localhost:8000/api/v1/memory/search \
  -H "X-API-Key: cc_career_a7f2k9m3" \
  -H "Content-Type: application/json" \
  -d '{"query":"melon trendcard","project":"bladina","limit":5}' | python3 -m json.tool
```

### Key Difference

| Method | Where it goes | Cloud sync? |
|:---|:---|:---|
| ❌ Cognee MCP tools | Local Cognee DB | No |
| ✅ Memory Hub API (curl localhost:8000) | Qdrant Cloud via mem0 | **Yes** |

The Memory Hub API is the bridge to Qdrant Cloud. Always use `curl` to `localhost:8000/api/v1/memory` for shared memories.
