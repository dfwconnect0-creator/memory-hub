"""Phase 5 — CrewAI adapter tests (RED phase)."""
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


def test_tool_exists():
    from adapters.crewai_tool import MemoryHubTool
    tool = MemoryHubTool(project="p1", agent_id="a1", api_key="k")
    assert tool.name
    assert tool.description


def test_tool_has_run_method():
    from adapters.crewai_tool import MemoryHubTool
    tool = MemoryHubTool(project="p1", agent_id="a1", api_key="k")
    assert callable(getattr(tool, "_run", None)) or callable(getattr(tool, "run", None))


def test_add_action_posts_to_memory_endpoint():
    from adapters.crewai_tool import MemoryHubTool
    mock = _mock_http({"memory_id": "m1", "status": "ok"})
    with patch("adapters.crewai_tool.httpx.Client", return_value=mock):
        tool = MemoryHubTool(project="content-creation", agent_id="writer_agent", api_key="k")
        tool._run(action="add", content="Brand voice tip")
    url = mock.post.call_args.args[0]
    assert "/api/v1/memory" in url


def test_add_action_sends_project_scope():
    from adapters.crewai_tool import MemoryHubTool
    mock = _mock_http({"memory_id": "m1", "status": "ok"})
    with patch("adapters.crewai_tool.httpx.Client", return_value=mock):
        tool = MemoryHubTool(project="seo-audit", agent_id="seo_agent", api_key="k")
        tool._run(action="add", content="Keyword tip")
    body = mock.post.call_args.kwargs["json"]
    assert body["project"] == "seo-audit"
    assert body["agent_id"] == "seo_agent"


def test_add_action_sends_auth_header():
    from adapters.crewai_tool import MemoryHubTool
    mock = _mock_http({"memory_id": "m1", "status": "ok"})
    with patch("adapters.crewai_tool.httpx.Client", return_value=mock):
        tool = MemoryHubTool(project="p1", agent_id="a1", api_key="crew-secret")
        tool._run(action="add", content="test")
    assert mock.post.call_args.kwargs["headers"]["X-API-Key"] == "crew-secret"


def test_search_action_posts_to_search_endpoint():
    from adapters.crewai_tool import MemoryHubTool
    mock = _mock_http({"results": [], "total": 0, "query": "q", "project": "p"})
    with patch("adapters.crewai_tool.httpx.Client", return_value=mock):
        tool = MemoryHubTool(project="p1", agent_id="a1", api_key="k")
        tool._run(action="search", query="ramadan")
    url = mock.post.call_args.args[0]
    assert "/api/v1/memory/search" in url


def test_search_action_sends_project_scope():
    from adapters.crewai_tool import MemoryHubTool
    mock = _mock_http({"results": [], "total": 0, "query": "q", "project": "personal"})
    with patch("adapters.crewai_tool.httpx.Client", return_value=mock):
        tool = MemoryHubTool(project="personal", agent_id="career_coach_agent", api_key="k")
        tool._run(action="search", query="job tips")
    body = mock.post.call_args.kwargs["json"]
    assert body["project"] == "personal"


def test_run_returns_json_string():
    from adapters.crewai_tool import MemoryHubTool
    mock = _mock_http({"memory_id": "m1", "status": "ok"})
    with patch("adapters.crewai_tool.httpx.Client", return_value=mock):
        tool = MemoryHubTool(project="p1", agent_id="a1", api_key="k")
        result = tool._run(action="add", content="test")
    data = json.loads(result)
    assert "memory_id" in data or "results" in data or "status" in data


def test_default_base_url():
    from adapters.crewai_tool import MemoryHubTool
    tool = MemoryHubTool(project="p1", agent_id="a1", api_key="k")
    assert "localhost:8000" in tool._base_url
