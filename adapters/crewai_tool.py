"""CrewAI adapter — wraps Memory Hub REST API as a CrewAI-compatible tool.

Install requirements:  pip install httpx
Optional framework:    pip install crewai

Usage::

    from adapters.crewai_tool import MemoryHubTool

    memory = MemoryHubTool(
        project="content-creation",
        agent_id="writer_agent",
        api_key="crew_writer_xxx",
    )
    # Assign to a CrewAI Agent's tools list
    agent = Agent(role="Writer", tools=[memory], ...)
"""
from __future__ import annotations

import json
from typing import Any

import httpx

# ── Optional CrewAI base (duck-typed if not installed) ────────────────────────
try:
    from crewai.tools import BaseTool as _BaseTool
except ImportError:
    _BaseTool = object  # type: ignore[assignment, misc]


class MemoryHubTool(_BaseTool):  # type: ignore[misc]
    """Single CrewAI tool covering both add and search via an `action` parameter."""

    name: str = "memory_hub"
    description: str = (
        "Add or search memories in the Memory Hub. "
        "Use action='add' with content=<text> and optional category=<cat> to store. "
        "Use action='search' with query=<text> and optional limit=<int> to retrieve."
    )

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

    def _run(
        self,
        action: str = "search",
        content: str = "",
        query: str = "",
        category: str = "general",
        limit: int = 10,
    ) -> str:
        if action == "add":
            result = self._post("/api/v1/memory", {
                "content": content,
                "project": self.project,
                "agent_id": self.agent_id,
                "category": category,
            })
        else:
            result = self._post("/api/v1/memory/search", {
                "query": query or content,
                "project": self.project,
                "limit": limit,
            })
        return json.dumps(result)

    def run(self, **kwargs: Any) -> str:
        """CrewAI calls this method when the tool is invoked."""
        return self._run(**kwargs)
