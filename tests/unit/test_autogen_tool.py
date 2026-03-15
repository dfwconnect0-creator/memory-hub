"""Phase 5 — AutoGen adapter tests (RED phase)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


def _mock_http(response_body: dict):
    mock_instance = MagicMock()
    mock_instance.__enter__ = MagicMock(return_value=mock_instance)
    mock_instance.__exit__ = MagicMock(return_value=False)
    mock_instance.post.return_value.json.return_value = response_body
    mock_instance.post.return_value.raise_for_status.return_value = None
    return mock_instance


def test_functions_class_exists():
    from adapters.autogen_tool import MemoryHubFunctions
    hub = MemoryHubFunctions(project="dev-tools", agent_id="claude_code_agent", api_key="k")
    assert hub is not None


def test_has_memory_add_callable():
    from adapters.autogen_tool import MemoryHubFunctions
    hub = MemoryHubFunctions(project="dev-tools", agent_id="a1", api_key="k")
    assert callable(hub.memory_add)


def test_has_memory_search_callable():
    from adapters.autogen_tool import MemoryHubFunctions
    hub = MemoryHubFunctions(project="dev-tools", agent_id="a1", api_key="k")
    assert callable(hub.memory_search)


def test_has_function_map():
    from adapters.autogen_tool import MemoryHubFunctions
    hub = MemoryHubFunctions(project="dev-tools", agent_id="a1", api_key="k")
    assert "memory_add" in hub.function_map
    assert "memory_search" in hub.function_map


def test_has_function_schemas():
    from adapters.autogen_tool import MemoryHubFunctions
    hub = MemoryHubFunctions(project="dev-tools", agent_id="a1", api_key="k")
    names = {s["name"] for s in hub.function_schemas}
    assert "memory_add" in names
    assert "memory_search" in names


def test_memory_add_posts_correct_endpoint():
    from adapters.autogen_tool import MemoryHubFunctions
    mock = _mock_http({"memory_id": "ag-1", "status": "ok"})
    with patch("adapters.autogen_tool.httpx.Client", return_value=mock):
        hub = MemoryHubFunctions(project="dev-tools", agent_id="claude_code_agent", api_key="k")
        hub.memory_add(content="Code pattern found")
    url = mock.post.call_args.args[0]
    assert "/api/v1/memory" in url


def test_memory_add_sends_project_scope():
    from adapters.autogen_tool import MemoryHubFunctions
    mock = _mock_http({"memory_id": "ag-1", "status": "ok"})
    with patch("adapters.autogen_tool.httpx.Client", return_value=mock):
        hub = MemoryHubFunctions(project="dev-tools", agent_id="opencode_agent", api_key="k")
        hub.memory_add(content="test")
    body = mock.post.call_args.kwargs["json"]
    assert body["project"] == "dev-tools"
    assert body["agent_id"] == "opencode_agent"


def test_memory_add_sends_auth_header():
    from adapters.autogen_tool import MemoryHubFunctions
    mock = _mock_http({"memory_id": "ag-1", "status": "ok"})
    with patch("adapters.autogen_tool.httpx.Client", return_value=mock):
        hub = MemoryHubFunctions(project="p1", agent_id="a1", api_key="autogen-key")
        hub.memory_add(content="test")
    assert mock.post.call_args.kwargs["headers"]["X-API-Key"] == "autogen-key"


def test_memory_search_posts_correct_endpoint():
    from adapters.autogen_tool import MemoryHubFunctions
    mock = _mock_http({"results": [], "total": 0, "query": "q", "project": "p"})
    with patch("adapters.autogen_tool.httpx.Client", return_value=mock):
        hub = MemoryHubFunctions(project="dev-tools", agent_id="a1", api_key="k")
        hub.memory_search(query="test query")
    url = mock.post.call_args.args[0]
    assert "/api/v1/memory/search" in url


def test_memory_search_sends_project_scope():
    from adapters.autogen_tool import MemoryHubFunctions
    mock = _mock_http({"results": [], "total": 0, "query": "q", "project": "content-creation"})
    with patch("adapters.autogen_tool.httpx.Client", return_value=mock):
        hub = MemoryHubFunctions(project="content-creation", agent_id="video_agent", api_key="k")
        hub.memory_search(query="video ideas")
    body = mock.post.call_args.kwargs["json"]
    assert body["project"] == "content-creation"


def test_memory_add_returns_json_string():
    from adapters.autogen_tool import MemoryHubFunctions
    mock = _mock_http({"memory_id": "ag-1", "status": "ok"})
    with patch("adapters.autogen_tool.httpx.Client", return_value=mock):
        hub = MemoryHubFunctions(project="p1", agent_id="a1", api_key="k")
        result = hub.memory_add(content="test")
    data = json.loads(result)
    assert "memory_id" in data


def test_memory_search_returns_json_string():
    from adapters.autogen_tool import MemoryHubFunctions
    mock = _mock_http({"results": [], "total": 0, "query": "q", "project": "p"})
    with patch("adapters.autogen_tool.httpx.Client", return_value=mock):
        hub = MemoryHubFunctions(project="p1", agent_id="a1", api_key="k")
        result = hub.memory_search(query="test")
    data = json.loads(result)
    assert "results" in data


def test_default_base_url():
    from adapters.autogen_tool import MemoryHubFunctions
    hub = MemoryHubFunctions(project="p1", agent_id="a1", api_key="k")
    assert "localhost:8000" in hub._base_url
