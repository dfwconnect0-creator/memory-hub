"""AutoGen adapter — wraps Memory Hub REST API as AutoGen function-call tools.

Install requirements:  pip install httpx
Optional framework:    pip install pyautogen   (or autogen-agentchat)

Usage::

    from adapters.autogen_tool import MemoryHubFunctions

    hub = MemoryHubFunctions(
        project="dev-tools",
        agent_id="claude_code_agent",
        api_key="ag_claude_xxx",
    )

    # Register with AutoGen ConversableAgent
    assistant.register_function(function_map=hub.function_map)
    # Or pass schemas to llm_config
    llm_config = {"functions": hub.function_schemas, ...}
"""
from __future__ import annotations

import json
from typing import Any

import httpx


class MemoryHubFunctions:
    """Factory that produces AutoGen-compatible callables + JSON schemas."""

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
        self._build_callables()
        self._build_schemas()

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client() as c:
            r = c.post(f"{self._base_url}{path}", json=body, headers=self._headers)
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]

    def _build_callables(self) -> None:
        def memory_add(content: str, category: str = "general") -> str:
            result = self._post("/api/v1/memory", {
                "content": content,
                "project": self.project,
                "agent_id": self.agent_id,
                "category": category,
            })
            return json.dumps(result)

        def memory_search(query: str, limit: int = 10) -> str:
            result = self._post("/api/v1/memory/search", {
                "query": query,
                "project": self.project,
                "limit": limit,
            })
            return json.dumps(result)

        self.memory_add = memory_add
        self.memory_search = memory_search
        self.function_map: dict[str, Any] = {
            "memory_add": memory_add,
            "memory_search": memory_search,
        }

    def _build_schemas(self) -> None:
        self.function_schemas: list[dict[str, Any]] = [
            {
                "name": "memory_add",
                "description": (
                    f"Store a memory scoped to project={self.project!r}. "
                    "category: trend|brand|campaign|audience|career|task|code|general"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "The memory text to store"},
                        "category": {"type": "string", "default": "general"},
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "memory_search",
                "description": (
                    f"Search memories in project={self.project!r} using semantic search."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            },
        ]
