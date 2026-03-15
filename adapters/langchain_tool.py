"""LangChain adapter — wraps Memory Hub REST API as LangChain-compatible tools.

Install requirements:  pip install httpx
Optional framework:    pip install langchain-core

Usage::

    from adapters.langchain_tool import MemoryAddTool, MemorySearchTool

    COMMON = dict(
        project="content-creation",
        agent_id="research_agent",
        api_key="lc_research_a8f3k2m1",
    )
    tools = [MemoryAddTool(**COMMON), MemorySearchTool(**COMMON)]
    # Pass tools to initialize_agent / create_react_agent as usual
"""
from __future__ import annotations

import json
from typing import Any

import httpx

# ── Optional LangChain base (duck-typed if not installed) ─────────────────────
try:
    from langchain_core.tools import BaseTool as _BaseTool
except ImportError:
    _BaseTool = object  # type: ignore[assignment, misc]


class _MemoryHubHTTP:
    """Shared HTTP helper — not a LangChain class."""

    def __init__(
        self,
        project: str,
        agent_id: str,
        api_key: str,
        base_url: str = "http://localhost:8000",
    ) -> None:
        self.project = project
        self.agent_id = agent_id
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client() as c:
            r = c.post(f"{self._base_url}{path}", json=body, headers=self._headers)
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]


class MemoryAddTool(_MemoryHubHTTP, _BaseTool):  # type: ignore[misc]
    """Store a memory in Memory Hub. Input: plain text or JSON with content + category."""

    name: str = "memory_add"
    description: str = (
        "Store a memory in the Memory Hub. "
        "Input: plain text, or JSON {content, category} where "
        "category ∈ trend|brand|campaign|audience|career|task|code|general."
    )

    def __init__(self, project: str, agent_id: str, api_key: str,
                 base_url: str = "http://localhost:8000", **kwargs: Any) -> None:
        _MemoryHubHTTP.__init__(self, project, agent_id, api_key, base_url)

    def _run(self, input: str) -> str:
        try:
            data: dict[str, Any] = json.loads(input) if input.lstrip().startswith("{") else {}
        except json.JSONDecodeError:
            data = {}
        result = self._post("/api/v1/memory", {
            "content": data.get("content", input),
            "project": self.project,
            "agent_id": self.agent_id,
            "category": data.get("category", "general"),
        })
        return json.dumps(result)

    async def _arun(self, input: str) -> str:
        return self._run(input)


class MemorySearchTool(_MemoryHubHTTP, _BaseTool):  # type: ignore[misc]
    """Search memories in Memory Hub. Input: plain query or JSON with query + limit."""

    name: str = "memory_search"
    description: str = (
        "Search memories in the Memory Hub using semantic search. "
        "Input: plain query string, or JSON {query, limit} (limit default 10)."
    )

    def __init__(self, project: str, agent_id: str, api_key: str,
                 base_url: str = "http://localhost:8000", **kwargs: Any) -> None:
        _MemoryHubHTTP.__init__(self, project, agent_id, api_key, base_url)

    def _run(self, input: str) -> str:
        try:
            data: dict[str, Any] = json.loads(input) if input.lstrip().startswith("{") else {}
        except json.JSONDecodeError:
            data = {}
        result = self._post("/api/v1/memory/search", {
            "query": data.get("query", input),
            "project": self.project,
            "limit": data.get("limit", 10),
        })
        return json.dumps(result)

    async def _arun(self, input: str) -> str:
        return self._run(input)
