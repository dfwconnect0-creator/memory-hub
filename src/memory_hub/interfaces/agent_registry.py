"""Protocol contract for agent registry backends."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from memory_hub.models.domain import AgentConfig


@runtime_checkable
class AgentRegistry(Protocol):
    """Any class implementing these methods can serve as the agent registry."""

    def get_agent(self, agent_id: str) -> AgentConfig | None:
        """Return AgentConfig for the given agent_id, or None if not found."""
        ...

    def list_agents(self) -> list[AgentConfig]:
        """Return all registered agents."""
        ...

    def validate_key(self, api_key: str) -> str | None:
        """Validate an API key. Returns agent_id if valid, None otherwise."""
        ...
