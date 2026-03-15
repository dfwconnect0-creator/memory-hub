"""Phase 5 — LangChain adapter tests (RED phase)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


def _mock_http(response_body: dict):
    """Return a patch target + configured mock that fakes httpx.Client."""
    mock_instance = MagicMock()
    mock_instance.__enter__ = MagicMock(return_value=mock_instance)
    mock_instance.__exit__ = MagicMock(return_value=False)
    mock_instance.post.return_value.json.return_value = response_body
    mock_instance.post.return_value.raise_for_status.return_value = None
    return mock_instance


# ── MemoryAddTool ─────────────────────────────────────────────────────────────

def test_add_tool_exists():
    from adapters.langchain_tool import MemoryAddTool
    tool = MemoryAddTool(project="p1", agent_id="a1", api_key="key")
    assert tool.name == "memory_add"
    assert tool.description


def test_add_tool_posts_to_memory_endpoint():
    from adapters.langchain_tool import MemoryAddTool
    mock = _mock_http({"memory_id": "m1", "status": "ok"})
    with patch("adapters.langchain_tool.httpx.Client", return_value=mock):
        tool = MemoryAddTool(project="content-creation", agent_id="research_agent", api_key="key")
        tool._run("Ramadan trend +40%")
    url = mock.post.call_args.args[0]
    assert "/api/v1/memory" in url


def test_add_tool_sends_project_scope():
    from adapters.langchain_tool import MemoryAddTool
    mock = _mock_http({"memory_id": "m1", "status": "ok"})
    with patch("adapters.langchain_tool.httpx.Client", return_value=mock):
        tool = MemoryAddTool(project="seo-audit", agent_id="seo_agent", api_key="key")
        tool._run("SEO content")
    body = mock.post.call_args.kwargs["json"]
    assert body["project"] == "seo-audit"
    assert body["agent_id"] == "seo_agent"


def test_add_tool_sends_auth_header():
    from adapters.langchain_tool import MemoryAddTool
    mock = _mock_http({"memory_id": "m1", "status": "ok"})
    with patch("adapters.langchain_tool.httpx.Client", return_value=mock):
        tool = MemoryAddTool(project="p1", agent_id="a1", api_key="secret-key")
        tool._run("test")
    headers = mock.post.call_args.kwargs["headers"]
    assert headers.get("X-API-Key") == "secret-key"


def test_add_tool_returns_json_string():
    from adapters.langchain_tool import MemoryAddTool
    mock = _mock_http({"memory_id": "m1", "status": "ok"})
    with patch("adapters.langchain_tool.httpx.Client", return_value=mock):
        tool = MemoryAddTool(project="p1", agent_id="a1", api_key="k")
        result = tool._run("test")
    data = json.loads(result)
    assert "memory_id" in data


def test_add_tool_json_input_with_category():
    from adapters.langchain_tool import MemoryAddTool
    mock = _mock_http({"memory_id": "m1", "status": "ok"})
    with patch("adapters.langchain_tool.httpx.Client", return_value=mock):
        tool = MemoryAddTool(project="p1", agent_id="a1", api_key="k")
        tool._run('{"content": "test", "category": "trend"}')
    body = mock.post.call_args.kwargs["json"]
    assert body["category"] == "trend"


def test_add_tool_default_base_url():
    from adapters.langchain_tool import MemoryAddTool
    tool = MemoryAddTool(project="p1", agent_id="a1", api_key="k")
    assert "localhost:8000" in tool._base_url


def test_add_tool_custom_base_url():
    from adapters.langchain_tool import MemoryAddTool
    tool = MemoryAddTool(project="p1", agent_id="a1", api_key="k", base_url="http://hub:9000")
    assert "hub:9000" in tool._base_url


# ── MemorySearchTool ──────────────────────────────────────────────────────────

def test_search_tool_exists():
    from adapters.langchain_tool import MemorySearchTool
    tool = MemorySearchTool(project="p1", agent_id="a1", api_key="key")
    assert tool.name == "memory_search"


def test_search_tool_posts_to_search_endpoint():
    from adapters.langchain_tool import MemorySearchTool
    mock = _mock_http({"results": [], "total": 0, "query": "test", "project": "p1"})
    with patch("adapters.langchain_tool.httpx.Client", return_value=mock):
        tool = MemorySearchTool(project="p1", agent_id="a1", api_key="key")
        tool._run("ramadan trends")
    url = mock.post.call_args.args[0]
    assert "/api/v1/memory/search" in url


def test_search_tool_sends_project_scope():
    from adapters.langchain_tool import MemorySearchTool
    mock = _mock_http({"results": [], "total": 0, "query": "test", "project": "content-creation"})
    with patch("adapters.langchain_tool.httpx.Client", return_value=mock):
        tool = MemorySearchTool(project="content-creation", agent_id="writer_agent", api_key="k")
        tool._run("trends")
    body = mock.post.call_args.kwargs["json"]
    assert body["project"] == "content-creation"


def test_search_tool_sends_auth_header():
    from adapters.langchain_tool import MemorySearchTool
    mock = _mock_http({"results": [], "total": 0, "query": "q", "project": "p"})
    with patch("adapters.langchain_tool.httpx.Client", return_value=mock):
        tool = MemorySearchTool(project="p1", agent_id="a1", api_key="my-key")
        tool._run("query")
    assert mock.post.call_args.kwargs["headers"]["X-API-Key"] == "my-key"


def test_search_tool_returns_json_string():
    from adapters.langchain_tool import MemorySearchTool
    mock = _mock_http({"results": [], "total": 0, "query": "q", "project": "p"})
    with patch("adapters.langchain_tool.httpx.Client", return_value=mock):
        tool = MemorySearchTool(project="p1", agent_id="a1", api_key="k")
        result = tool._run("query")
    data = json.loads(result)
    assert "results" in data
