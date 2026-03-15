# Memory Protocol for AI Agents (Framework Agnostic)

**Version:** 2.0  
**Project:** cognee-mcp  
**Date:** March 9, 2026

## 1. Goal
To provide a structured, lean, and debuggable memory architecture that ensures ANY AI agent framework (LangChain, AutoGen, CrewAI, MCP agents) can persist, search, and manage long-term project information without overloading the host.

## 2. Universal Access Protocol
All agents must interact via the **Unified Memory API (REST)** or **MCP Protocol**.

### A. Unified API (REST) - For LangChain, AutoGen, CrewAI
Agents connect via HTTP requests to `http://localhost:8000/api/v1`.

- **POST `/api/v1/memory`**: Add memory
- **GET `/api/v1/memory`**: Search memory
- **POST `/api/v1/memory/cognify`**: Run enrichment

### B. MCP Server - For OpenCode, Antigravity
Agents connect natively via the `cognee-mcp` MCP server endpoint.

## 3. Framework-Specific Adapters
Every agent framework must use a local **Memory Client Adapter** to ensure consistent formatting:

- **LangChain**: Use `CustomAPIWrapper` or `MemoryTool`.
- **AutoGen**: Use a custom `Tool` that calls the Memory API.
- **CrewAI**: Use a custom `Tool` for memory management.

## 4. Metadata Requirement (Mandatory)
Every request must include the framework and agent ID for logging and access control:

```json
{
  "agent_id": "crewai-researcher-01",
  "framework": "crewai",
  "project": "content-creation",
  "data": "..."
}
```

---
*End of Protocol v2*
