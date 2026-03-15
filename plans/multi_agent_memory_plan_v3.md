# Multi-Agent Memory Architecture Plan (v3)

**Goal:** Create a lean, debuggable, framework-agnostic persistent memory hub for AI agents.

## 1. Core Architecture: "The Memory Hub"
The central service is a FastAPI-based REST API that acts as a secure, authenticated bridge between any agent framework (LangChain, CrewAI, AutoGen) and Cognee.

### Key Components:
- **API Server:** Lightweight FastAPI wrapper.
- **Agent Registry:** A simple configuration (`config/agents.yaml`) mapping API keys to `agent_id`, `framework`, and `project_slug`.
- **Standardized API:** Uses `X-API-KEY` header for all requests to ensure a standard interface.

## 2. Integration Strategy: LangChain First
- **Connector:** Develop a custom `CogneeMemoryTool` class for LangChain.
- **Ease of Use:** Agents will import this tool and add it to their toolset. It will automatically inject metadata (agent_id, project_slug) into every memory request.

## 3. Lean Debugging (The "Three Metrics")
The dashboard/CLI surfaces only:
1. **Heartbeat:** Is the agent authenticated and responding?
2. **Ingestion Status:** Success/Failure rate of last 5 writes.
3. **Retrieval Efficiency:** Latency and success rate of last 5 search queries.

## 4. Implementation Roadmap
| Phase | Title | Focus |
| :--- | :--- | :--- |
| **1** | **Hub Foundation** | FastAPI server, API Key Auth, Request Logging (Trace IDs), Project-based storage. |
| **2** | **LangChain Adapter** | Develop the lean `CogneeMemoryTool` for LangChain. |
| **3** | **Nightly Pipeline** | Cron orchestration for summarization and graph generation. |
| **4** | **Lean Debug Dashboard** | Minimal dashboard for "Three Metrics" and query logs. |

## 5. Security & Maintenance
- **Auth:** `X-API-KEY` passed in headers.
- **Data Isolation:** All memory requests scoped to `project_slug` and `agent_id`.
- **Maintenance:** Heavy processing (cognification/summarization) deferred to async cronjob.
