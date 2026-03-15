# Memory Hub v5 — Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [0.1.0] — 2026-03-15

### 🎉 Initial Release — Full MVP

**Built in 3.5 hours** using Spec-Driven Development + Superpowers workflow.

### Added
- **Core Architecture** — Protocol interfaces, Pydantic models, dependency injection
- **Memory Service** — Scoped add/search/batch/delete/export with project + agent isolation
- **Mem0 Adapter** — Wraps mem0.Memory with Gemini Embedding 001 (768 dims, free tier)
- **REST API** — 6 FastAPI endpoints with app factory pattern
  - `POST /api/v1/memory` — Add a memory (201)
  - `POST /api/v1/memory/search` — Search memories
  - `POST /api/v1/memory/batch` — Batch add memories (201)
  - `GET /api/v1/memory/export` — Export project memories
  - `GET /api/v1/health` — Health check (public, no auth)
  - `GET /api/v1/agents` — List registered agents
- **MCP Server** — 3 tools for CLI agents (memory_add, memory_search, memory_status)
- **Auth Middleware** — X-API-Key header validation with 403 responses
- **Framework Adapters** — LangChain, CrewAI, AutoGen tool wrappers
- **Agent Registry** — 9 agents across 4 projects defined in `config/agents.yaml`
- **MCP Configs** — Ready-to-use configs for Claude Code, OpenCode, Antigravity
- **Full Test Suite** — 124 passing tests, 74% coverage
- **Documentation** — README, Quickstart, Architecture, Troubleshooting guides
- **Clean Code** — 0 ruff errors, 0 mypy errors (strict mode, 27 files)

### Technical Decisions
- **uv** over pip for package management
- **Gemini Embedding 001** over OpenAI embeddings (free, Arabic-native, 768 dims)
- **Gemini 2.5 Flash** as LLM provider (free tier)
- **Qdrant** in-process vector store (no external service for MVP)
- **Protocol interfaces** for backend swapping (mem0 → Cognee)
- **App factory pattern** for testability

### Development Credits
- **Architecture & Review:** Antigravity (Opus 4.6)
- **Implementation:** Claude CLI (Sonnet 4.6) — Phases 1-6
- **Decisions & Execution:** Mohamed Salah

### Git History
```
0a604b9 fix: use gemini-2.5-flash LLM and gemini-embedding-001 model names
69c2f2b feat(adapters): Phase 5+6 — framework adapters, README, mypy clean
dc875c4 feat(mcp): Phase 4 — MCP server for CLI agents
7ddbfe7 feat(api): Phase 3 — REST API with app factory
c86d5d7 feat(core): Phase 1+2 — interfaces, models, config, services, auth
902a0ed chore: bootstrap v5 with uv
```
