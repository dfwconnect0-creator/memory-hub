"""MCP server for CLI agents (OpenCode, Claude Code, Antigravity).

Agent identity is read from env vars at startup:
  AGENT_ID  — must match a key in config/agents.yaml
  AGENT_KEY — must be in AGENT_KEYS env var or equal HUB_API_KEY

Tools exposed:
  memory_add     — store a memory scoped to the agent's project
  memory_search  — semantic search within the agent's project
  memory_status  — return server status + current agent info

Run as MCP stdio server:
  uv run python -m memory_hub.transport.mcp.mcp_server
"""
from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from memory_hub.models.domain import MemoryCategory, SearchResult
from memory_hub.services.memory_service import MemoryService
from memory_hub.services.registry_service import RegistryService

# ── Shared state injected via lifespan ───────────────────────────────────────

@dataclass
class AgentState:
    """Runtime state available to every tool via ctx.request_context.lifespan_context."""

    memory_service: MemoryService
    registry: RegistryService
    agent_id: str
    project: str
    agent_name: str
    cognee_store: Any | None = None  # CogneeAdapter when COGNEE_ENABLED


# ── Business logic (pure functions — testable without MCP context) ────────────

async def handle_memory_add(
    state: AgentState,
    content: str,
    category: str = "general",
) -> dict[str, Any]:
    """Add a memory scoped to the agent's project. Returns a result dict."""
    try:
        cat = MemoryCategory(category)
    except ValueError:
        valid = [c.value for c in MemoryCategory]
        return {"error": f"Invalid category {category!r}. Valid: {valid}"}

    memory_id = await state.memory_service.add(
        content=content,
        project=state.project,
        agent_id=state.agent_id,
        category=cat,
    )
    return {
        "memory_id": memory_id,
        "project": state.project,
        "agent_id": state.agent_id,
        "status": "ok",
    }


async def handle_memory_search(
    state: AgentState,
    query: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Search memories scoped to the agent's project."""
    results: list[SearchResult] = await state.memory_service.search(
        query=query,
        project=state.project,
        agent_id=state.agent_id,
        limit=limit,
    )
    return {
        "results": [
            {
                "id": r.id,
                "content": r.content,
                "score": round(r.score, 4),
                "category": r.category.value,
            }
            for r in results
        ],
        "total": len(results),
        "query": query,
        "project": state.project,
    }


async def handle_memory_status(state: AgentState) -> dict[str, Any]:
    """Return server status + current agent information."""
    agent = state.registry.get_agent(state.agent_id)
    return {
        "status": "ok",
        "agent_id": state.agent_id,
        "agent_name": agent.name if agent else state.agent_name,
        "project": state.project,
        "framework": agent.framework if agent else "unknown",
    }


# ── Production lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def _production_lifespan(server: FastMCP) -> AsyncIterator[AgentState]:
    """Read AGENT_ID + AGENT_KEY from env, validate, wire services."""
    agent_id = os.environ.get("AGENT_ID", "")
    agent_key = os.environ.get("AGENT_KEY", "")

    if not agent_id or not agent_key:
        raise RuntimeError(
            "AGENT_ID and AGENT_KEY environment variables are required to start the MCP server."
        )

    from memory_hub.config import Settings, load_agents_config

    settings = Settings()  # type: ignore[call-arg]
    agents_data = load_agents_config(settings.AGENTS_YAML_PATH)
    registry = RegistryService(settings=settings, agents_data=agents_data)

    validated_id = registry.validate_key(agent_key)
    if validated_id is None:
        raise RuntimeError(f"Invalid AGENT_KEY for AGENT_ID={agent_id!r}")

    agent_config = registry.get_agent(agent_id)
    if agent_config is None:
        raise RuntimeError(f"Unknown AGENT_ID: {agent_id!r}. Check config/agents.yaml")

    from memory_hub.adapters.mem0_adapter import Mem0Adapter

    mem0_store = Mem0Adapter(settings)
    cognee_store = None

    if settings.COGNEE_ENABLED:
        from memory_hub.adapters.cognee_adapter import CogneeAdapter
        from memory_hub.services.dual_memory_service import DualMemoryService

        cognee_store = CogneeAdapter(settings)
        if settings.COGNEE_DUAL_WRITE:
            memory_service = DualMemoryService(
                mem0_store=mem0_store,
                cognee_store=cognee_store,
            )
        else:
            memory_service = MemoryService(store=mem0_store)
    else:
        memory_service = MemoryService(store=mem0_store)

    yield AgentState(
        memory_service=memory_service,
        registry=registry,
        agent_id=agent_id,
        project=agent_config.project,
        agent_name=agent_config.name,
        cognee_store=cognee_store,
    )


# ── Server factory ───────────────────────────────────────────────────────────

def create_mcp_server() -> FastMCP:
    """Create and return the MCP server. Safe to call multiple times (e.g. in tests)."""
    server: FastMCP = FastMCP("Memory Hub", lifespan=_production_lifespan)
    _register_tools(server)
    return server


def _register_tools(server: FastMCP) -> None:
    """Register all MCP tools onto the server instance."""

    @server.tool(
        description=(
            "Add a memory for the current agent. Automatically scoped to the agent's project. "
            "category: trend | brand | campaign | audience | career | task | code | general"
        )
    )
    async def memory_add(content: str, ctx: Context, category: str = "general") -> str:  # type: ignore[type-arg]
        state: AgentState = ctx.request_context.lifespan_context
        result = await handle_memory_add(state, content, category)
        return json.dumps(result)

    @server.tool(
        description=(
            "Search memories in the current agent's project using semantic search. "
            "Returns the most relevant results up to `limit`."
        )
    )
    async def memory_search(query: str, ctx: Context, limit: int = 10) -> str:  # type: ignore[type-arg]
        state: AgentState = ctx.request_context.lifespan_context
        result = await handle_memory_search(state, query, limit)
        return json.dumps(result)

    @server.tool(description="Get Memory Hub status and info about the current agent session.")
    async def memory_status(ctx: Context) -> str:  # type: ignore[type-arg]
        state: AgentState = ctx.request_context.lifespan_context
        result = await handle_memory_status(state)
        return json.dumps(result)

    @server.tool(
        description=(
            "Build a knowledge graph from recent memories using Cognee (local Neo4j + Ollama). "
            "This processes memories through entity extraction and relationship detection. "
            "Requires Neo4j and Ollama to be running. May take 30-120 seconds."
        )
    )
    async def memory_cognify(ctx: Context) -> str:  # type: ignore[type-arg]
        state: AgentState = ctx.request_context.lifespan_context
        if hasattr(state, "cognee_store") and state.cognee_store is not None:
            result = await state.cognee_store.cognify()
            return json.dumps(result)
        return json.dumps({"status": "error", "message": "Cognee is not enabled"})

    @server.tool(
        description=(
            "Deep search using Cognee's knowledge graph (Neo4j + LanceDB). "
            "Returns results from entity relationships and semantic embeddings. "
            "search_type: CHUNKS | GRAPH_COMPLETION | RAG_COMPLETION"
        )
    )
    async def memory_search_deep(  # type: ignore[type-arg]
        query: str,
        ctx: Context,
        search_type: str = "CHUNKS",
        limit: int = 10,
    ) -> str:
        state: AgentState = ctx.request_context.lifespan_context
        if hasattr(state, "cognee_store") and state.cognee_store is not None:
            results = await state.cognee_store.search(
                query=query,
                project=state.project,
                agent_id=state.agent_id,
                limit=limit,
            )
            return json.dumps({
                "results": [
                    {"content": r.content, "score": r.score, "source": "cognee"}
                    for r in results
                ],
                "total": len(results),
                "query": query,
                "search_type": search_type,
            })
        return json.dumps({"status": "error", "message": "Cognee is not enabled"})


# ── Module-level server + entry point ────────────────────────────────────────

mcp = create_mcp_server()

if __name__ == "__main__":
    mcp.run()
