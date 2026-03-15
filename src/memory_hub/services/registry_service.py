"""RegistryService: loads agents from YAML + validates API keys."""
from __future__ import annotations

from memory_hub.config import Settings
from memory_hub.models.domain import AgentConfig, AgentPermissions


class RegistryService:
    """Implements AgentRegistry Protocol. Loaded once at startup."""

    def __init__(self, settings: Settings, agents_data: dict) -> None:  # type: ignore[type-arg]
        self._settings = settings
        self._agents: dict[str, AgentConfig] = self._parse_agents(agents_data)

    def _parse_agents(self, data: dict) -> dict[str, AgentConfig]:  # type: ignore[type-arg]
        result: dict[str, AgentConfig] = {}
        for agent_id, raw in (data.get("agents") or {}).items():
            perms_raw = raw.get("permissions", {})
            permissions = AgentPermissions(
                read_shared=perms_raw.get("read_shared", True),
                write_shared=perms_raw.get("write_shared", True),
            )
            result[agent_id] = AgentConfig(
                name=raw["name"],
                framework=raw["framework"],
                project=raw["project"],
                role=raw["role"],
                other_mcps=raw.get("other_mcps", []),
                permissions=permissions,
            )
        return result

    def get_agent(self, agent_id: str) -> AgentConfig | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[AgentConfig]:
        return list(self._agents.values())

    def validate_key(self, api_key: str) -> str | None:
        """Returns agent_id if the API key is valid. None otherwise."""
        # Master hub key is valid for any agent
        if api_key == self._settings.HUB_API_KEY:
            return "hub"
        # Per-agent keys from AGENT_KEYS env var
        return self._settings.agent_key_map.get(api_key)
