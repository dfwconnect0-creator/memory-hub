"""HealthService: health check and basic metrics."""
from __future__ import annotations

from typing import Any

from memory_hub.services.registry_service import RegistryService

_VERSION = "0.1.0"


class HealthService:
    def __init__(self, registry: RegistryService) -> None:
        self._registry = registry

    async def check_health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "version": _VERSION,
            "agents_registered": len(self._registry.list_agents()),
        }

    async def get_metrics(self) -> dict[str, Any]:
        return {
            "agents_registered": len(self._registry.list_agents()),
        }
