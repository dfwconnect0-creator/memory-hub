"""Agent routes: GET /agents — list all registered agents."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from memory_hub.services.registry_service import RegistryService
from memory_hub.transport.rest.deps import get_registry

router = APIRouter(tags=["agents"])


@router.get("/agents")
async def list_agents(
    registry: RegistryService = Depends(get_registry),
) -> dict:  # type: ignore[type-arg]
    agents = registry.list_agents()
    return {
        "agents": [a.model_dump() for a in agents],
        "count": len(agents),
    }
