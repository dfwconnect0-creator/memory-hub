# Enable Cloud Qdrant on Ubuntu — Quick Setup

**Date:** 2026-03-17 | **Machine:** Ubuntu PC
**Prereqs:** `cognee-mcp` repo cloned, Memory Hub running

---

## Steps

### 1. Pull the latest code (already has Qdrant Cloud support)

```bash
cd ~/cognee-mcp
git pull origin master
```

This pulls the `feat(memory): add Qdrant Cloud support for cross-machine sync` commit which modified:
- `src/memory_hub/config.py` — added `QDRANT_URL` and `QDRANT_API_KEY` optional fields
- `src/memory_hub/adapters/mem0_adapter.py` — cloud vs local Qdrant mode switch

### 2. Add these lines to your `.env` file

Open `~/cognee-mcp/.env` and add these at the end:

```bash
# Redirect mem0 internal dir (avoids permission issues)
MEM0_DIR=/tmp/mem0_storage

# Qdrant Cloud — shared with Mac for cross-machine memory sync
QDRANT_URL=https://7ea06f99-21fa-4c5e-a0aa-e39107c5f9f2.eu-west-1-0.aws.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.oQkXy1XQRUQfZiCrL47T10KlUn8np8OtB6o9UhKUY_s
```

### 3. Restart the Memory Hub server

```bash
# Kill existing server
kill $(lsof -ti:8000) 2>/dev/null; sleep 1

# Start with cloud Qdrant
cd ~/cognee-mcp
MEM0_DIR=/tmp/mem0_storage uv run uvicorn src.memory_hub.app:create_app --factory --port 8000
```

You should see in the logs: `Qdrant: using cloud at https://7ea06f99...`

### 4. Verify — search for the memory we stored from Mac

```bash
curl -s -X POST "http://localhost:8000/api/v1/memory/search" \
  -H "X-API-Key: cc_career_a7f2k9m3" \
  -H "Content-Type: application/json" \
  -d '{"query":"cloud qdrant test Mac","project":"bladina","limit":3}' | python3 -m json.tool
```

If you see results about "Cloud Qdrant migration test" and "Writing from Mac" — **both machines are sharing the same brain!** 🧠

### 5. Write a test memory from Ubuntu

```bash
curl -s -X POST http://localhost:8000/api/v1/memory \
  -H "X-API-Key: cc_career_a7f2k9m3" \
  -H "Content-Type: application/json" \
  -d '{"content":"First memory from Ubuntu! Cloud sync is working.","category":"general","project":"bladina","agent_id":"career_coach_agent"}' | python3 -m json.tool
```

Then go back to Mac and search for it to confirm two-way sync.
