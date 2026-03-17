"""Unit tests for CogneeAdapter and DualMemoryService.

Tests use mocks — no real Cognee/Neo4j/Ollama required.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memory_hub.models.domain import MemoryCategory, MemoryEntry, SearchResult


# ── CogneeAdapter Tests ─────────────────────────────────────────────────────


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.COGNEE_PYTHON_PATH = "/usr/bin/python3"
    settings.COGNEE_ENV_PATH = "/tmp/cognee-test/.env"
    settings.COGNEE_SEARCH_TYPE = "CHUNKS"
    settings.COGNEE_AUTO_COGNIFY = False  # Disable auto-cognify in tests
    return settings


@pytest.fixture
def cognee_adapter(mock_settings):
    from memory_hub.adapters.cognee_adapter import CogneeAdapter

    return CogneeAdapter(mock_settings)


@pytest.fixture
def sample_entry():
    return MemoryEntry(
        content="AI trends for 2026 include agentic systems",
        project="dev-tools",
        agent_id="antigravity_agent",
        category=MemoryCategory.TREND,
    )


async def test_add_returns_cognee_prefixed_id(cognee_adapter, sample_entry):
    """add() should return an ID starting with 'cognee-'."""
    with patch.object(cognee_adapter, "_run_cognee", new_callable=AsyncMock) as mock:
        mock.return_value = {"status": "ok", "action": "add"}
        result = await cognee_adapter.add(sample_entry)
        assert result.startswith("cognee-")


async def test_add_calls_run_cognee_with_add_action(cognee_adapter, sample_entry):
    """add() should call _run_cognee with action='add'."""
    with patch.object(cognee_adapter, "_run_cognee", new_callable=AsyncMock) as mock:
        mock.return_value = {"status": "ok", "action": "add"}
        await cognee_adapter.add(sample_entry)
        mock.assert_called_once_with("add", content=sample_entry.content)


async def test_add_returns_empty_on_failure(cognee_adapter, sample_entry):
    """add() should return empty string when Cognee fails."""
    with patch.object(cognee_adapter, "_run_cognee", new_callable=AsyncMock) as mock:
        mock.return_value = {"status": "error", "message": "Neo4j unreachable"}
        result = await cognee_adapter.add(sample_entry)
        assert result == ""


async def test_search_returns_search_results(cognee_adapter):
    """search() should return SearchResult objects."""
    with patch.object(cognee_adapter, "_run_cognee", new_callable=AsyncMock) as mock:
        mock.return_value = {
            "status": "ok",
            "results": [
                {"content": "AI trends 2026", "score": 0.85},
                {"content": "Agentic systems overview", "score": 0.72},
            ],
        }
        results = await cognee_adapter.search(
            query="AI trends",
            project="dev-tools",
            limit=5,
        )
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].content == "AI trends 2026"
        assert results[0].score == 0.85
        assert results[0].metadata["source"] == "cognee"


async def test_search_returns_empty_on_failure(cognee_adapter):
    """search() should return empty list when Cognee fails."""
    with patch.object(cognee_adapter, "_run_cognee", new_callable=AsyncMock) as mock:
        mock.return_value = {"status": "error", "message": "Ollama down"}
        results = await cognee_adapter.search(query="test", project="p")
        assert results == []


async def test_cognify_delegates_to_run_cognee(cognee_adapter):
    """cognify() should call _run_cognee with action='cognify'."""
    with patch.object(cognee_adapter, "_run_cognee", new_callable=AsyncMock) as mock:
        mock.return_value = {"status": "ok", "action": "cognify"}
        result = await cognee_adapter.cognify()
        assert result["status"] == "ok"
        mock.assert_called_once_with("cognify")


async def test_status_returns_cognee_version(cognee_adapter):
    """status() should return Cognee version info."""
    with patch.object(cognee_adapter, "_run_cognee", new_callable=AsyncMock) as mock:
        mock.return_value = {"status": "ok", "cognee_version": "0.5.4"}
        result = await cognee_adapter.status()
        assert result["cognee_version"] == "0.5.4"


# ── DualMemoryService Tests ─────────────────────────────────────────────────


@pytest.fixture
def mock_mem0_store():
    store = AsyncMock()
    store.add.return_value = "mem0-id-123"
    store.search.return_value = [
        SearchResult(
            id="m1",
            content="mem0 result",
            project="dev-tools",
            agent_id="agent",
            score=0.9,
        )
    ]
    return store


@pytest.fixture
def mock_cognee_store():
    store = AsyncMock()
    store.add.return_value = "cognee-id-456"
    store.search.return_value = [
        SearchResult(
            id="c1",
            content="cognee result",
            project="dev-tools",
            agent_id="agent",
            score=0.8,
            metadata={"source": "cognee"},
        )
    ]
    store.cognify.return_value = {"status": "ok"}
    return store


@pytest.fixture
def dual_service(mock_mem0_store, mock_cognee_store):
    from memory_hub.services.dual_memory_service import DualMemoryService

    return DualMemoryService(
        mem0_store=mock_mem0_store,
        cognee_store=mock_cognee_store,
    )


async def test_dual_add_returns_mem0_id(dual_service, mock_mem0_store):
    """add() should return the mem0 ID (fast path)."""
    result = await dual_service.add(
        content="test content",
        project="dev-tools",
        agent_id="agent",
    )
    assert result == "mem0-id-123"
    mock_mem0_store.add.assert_called_once()


async def test_dual_search_merges_results(dual_service):
    """search() should merge results from both backends."""
    results = await dual_service.search(
        query="test query",
        project="dev-tools",
        limit=10,
    )
    assert len(results) == 2
    assert results[0].content == "mem0 result"  # primary first
    assert results[1].content == "cognee result"  # secondary appended


async def test_dual_search_deduplicates(dual_service, mock_mem0_store, mock_cognee_store):
    """search() should deduplicate identical content from both backends."""
    mock_cognee_store.search.return_value = [
        SearchResult(
            id="c1",
            content="mem0 result",  # same as mem0
            project="dev-tools",
            agent_id="agent",
            score=0.7,
        )
    ]
    results = await dual_service.search(
        query="test",
        project="dev-tools",
        limit=10,
    )
    assert len(results) == 1  # deduplicated


async def test_dual_search_survives_cognee_failure(
    dual_service, mock_mem0_store, mock_cognee_store
):
    """search() should still work if Cognee fails."""
    mock_cognee_store.search.side_effect = Exception("Cognee crashed")
    results = await dual_service.search(
        query="test",
        project="dev-tools",
        limit=10,
    )
    assert len(results) == 1
    assert results[0].content == "mem0 result"


async def test_dual_cognify_delegates_to_cognee(dual_service, mock_cognee_store):
    """cognify() should delegate to the Cognee store."""
    result = await dual_service.cognify()
    assert result["status"] == "ok"
    mock_cognee_store.cognify.assert_called_once()


# ── MCP Server — New Tools Registration ──────────────────────────────────────


def test_mcp_server_has_cognify_tool():
    """MCP server should register memory_cognify tool."""
    from memory_hub.transport.mcp.mcp_server import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "memory_cognify" in tool_names


def test_mcp_server_has_search_deep_tool():
    """MCP server should register memory_search_deep tool."""
    from memory_hub.transport.mcp.mcp_server import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "memory_search_deep" in tool_names
