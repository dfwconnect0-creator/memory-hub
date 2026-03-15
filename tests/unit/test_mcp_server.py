"""Phase 4 — MCP server tests (RED phase).

Strategy:
- Test business logic functions (handle_*) directly with mock AgentState
- Test server creation + tool registration without running stdio
- No real mem0/Gemini/qdrant needed
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from memory_hub.models.domain import MemoryCategory, SearchResult

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_memory_service():
    svc = AsyncMock()
    svc.add.return_value = "mcp-mem-001"
    svc.search.return_value = []
    return svc


@pytest.fixture
def mock_registry():
    reg = MagicMock()
    reg.get_agent.return_value = MagicMock(
        name="Claude Code CLI Agent",
        framework="mcp",
        project="dev-tools",
    )
    return reg


@pytest.fixture
def agent_state(mock_memory_service, mock_registry):
    from memory_hub.transport.mcp.mcp_server import AgentState

    return AgentState(
        memory_service=mock_memory_service,
        registry=mock_registry,
        agent_id="claude_code_agent",
        project="dev-tools",
        agent_name="Claude Code CLI Agent",
    )


# ── Server creation ───────────────────────────────────────────────────────────

def test_create_mcp_server_returns_fastmcp():
    from mcp.server.fastmcp import FastMCP

    from memory_hub.transport.mcp.mcp_server import create_mcp_server

    server = create_mcp_server()
    assert isinstance(server, FastMCP)


def test_server_has_memory_add_tool():
    from memory_hub.transport.mcp.mcp_server import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "memory_add" in tool_names


def test_server_has_memory_search_tool():
    from memory_hub.transport.mcp.mcp_server import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "memory_search" in tool_names


def test_server_has_memory_status_tool():
    from memory_hub.transport.mcp.mcp_server import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "memory_status" in tool_names


def test_server_name_is_memory_hub():
    from memory_hub.transport.mcp.mcp_server import create_mcp_server

    server = create_mcp_server()
    assert "Memory Hub" in server.name


# ── handle_memory_add ────────────────────────────────────────────────────────

async def test_add_scoped_to_agent_project(agent_state, mock_memory_service):
    from memory_hub.transport.mcp.mcp_server import handle_memory_add

    await handle_memory_add(agent_state, "Hello from CLI", "general")

    mock_memory_service.add.assert_called_once()
    call_kwargs = mock_memory_service.add.call_args.kwargs
    assert call_kwargs["project"] == "dev-tools"
    assert call_kwargs["agent_id"] == "claude_code_agent"


async def test_add_returns_memory_id(agent_state):
    from memory_hub.transport.mcp.mcp_server import handle_memory_add

    result = await handle_memory_add(agent_state, "test content")
    assert result["memory_id"] == "mcp-mem-001"
    assert result["status"] == "ok"


async def test_add_includes_project_in_response(agent_state):
    from memory_hub.transport.mcp.mcp_server import handle_memory_add

    result = await handle_memory_add(agent_state, "test")
    assert result["project"] == "dev-tools"


async def test_add_invalid_category_returns_error(agent_state):
    from memory_hub.transport.mcp.mcp_server import handle_memory_add

    result = await handle_memory_add(agent_state, "test", category="invalid_cat")
    assert "error" in result


async def test_add_valid_categories_accepted(agent_state):
    from memory_hub.transport.mcp.mcp_server import handle_memory_add

    for cat in ["trend", "code", "task", "general", "career"]:
        result = await handle_memory_add(agent_state, f"test {cat}", category=cat)
        assert "error" not in result, f"category {cat!r} should be valid"


# ── handle_memory_search ─────────────────────────────────────────────────────

async def test_search_scoped_to_agent_project(agent_state, mock_memory_service):
    from memory_hub.transport.mcp.mcp_server import handle_memory_search

    await handle_memory_search(agent_state, "test query")

    mock_memory_service.search.assert_called_once()
    call_kwargs = mock_memory_service.search.call_args.kwargs
    assert call_kwargs["project"] == "dev-tools"


async def test_search_passes_agent_id(agent_state, mock_memory_service):
    from memory_hub.transport.mcp.mcp_server import handle_memory_search

    await handle_memory_search(agent_state, "test query")

    call_kwargs = mock_memory_service.search.call_args.kwargs
    assert call_kwargs["agent_id"] == "claude_code_agent"


async def test_search_respects_limit(agent_state, mock_memory_service):
    from memory_hub.transport.mcp.mcp_server import handle_memory_search

    await handle_memory_search(agent_state, "test", limit=5)
    call_kwargs = mock_memory_service.search.call_args.kwargs
    assert call_kwargs["limit"] == 5


async def test_search_response_shape(agent_state):
    from memory_hub.transport.mcp.mcp_server import handle_memory_search

    result = await handle_memory_search(agent_state, "test")
    assert "results" in result
    assert "total" in result
    assert "query" in result
    assert "project" in result


async def test_search_returns_results(agent_state, mock_memory_service):
    from memory_hub.transport.mcp.mcp_server import handle_memory_search

    mock_memory_service.search.return_value = [
        SearchResult(
            id="m1",
            content="Code snippet for auth",
            project="dev-tools",
            agent_id="claude_code_agent",
            score=0.92,
            category=MemoryCategory.CODE,
        )
    ]
    result = await handle_memory_search(agent_state, "auth")
    assert result["total"] == 1
    assert result["results"][0]["content"] == "Code snippet for auth"
    assert result["results"][0]["category"] == "code"


# ── handle_memory_status ─────────────────────────────────────────────────────

async def test_status_returns_ok(agent_state):
    from memory_hub.transport.mcp.mcp_server import handle_memory_status

    result = await handle_memory_status(agent_state)
    assert result["status"] == "ok"


async def test_status_includes_agent_info(agent_state):
    from memory_hub.transport.mcp.mcp_server import handle_memory_status

    result = await handle_memory_status(agent_state)
    assert result["agent_id"] == "claude_code_agent"
    assert result["project"] == "dev-tools"


async def test_status_includes_agent_name(agent_state):
    from memory_hub.transport.mcp.mcp_server import handle_memory_status

    result = await handle_memory_status(agent_state)
    assert "agent_name" in result


# ── Project isolation ────────────────────────────────────────────────────────

async def test_add_cannot_escape_agent_project(mock_memory_service, mock_registry):
    """Even if the caller tries to inject a different project, scoping is enforced."""
    from memory_hub.transport.mcp.mcp_server import AgentState, handle_memory_add

    state = AgentState(
        memory_service=mock_memory_service,
        registry=mock_registry,
        agent_id="seo_agent",
        project="seo-audit",
        agent_name="SEO Audit Agent",
    )
    # Caller passes content — project is always taken from state, not from caller
    await handle_memory_add(state, "SEO content")
    call_kwargs = mock_memory_service.add.call_args.kwargs
    assert call_kwargs["project"] == "seo-audit"


async def test_search_cannot_escape_agent_project(mock_memory_service, mock_registry):
    """Search always uses the agent's own project — no cross-project leakage."""
    from memory_hub.transport.mcp.mcp_server import AgentState, handle_memory_search

    state = AgentState(
        memory_service=mock_memory_service,
        registry=mock_registry,
        agent_id="research_agent",
        project="content-creation",
        agent_name="Research Agent",
    )
    await handle_memory_search(state, "ramadan trends")
    call_kwargs = mock_memory_service.search.call_args.kwargs
    assert call_kwargs["project"] == "content-creation"
