"""Health route: GET /health — public, no auth required."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from memory_hub.services.health_service import HealthService
from memory_hub.transport.rest.deps import get_health_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    request: Request,
    service: HealthService = Depends(get_health_service),
) -> dict[str, Any]:
    result = await service.check_health()
    settings = getattr(request.app.state, "settings", None)
    result["storage_mode"] = "local"
    result["sync_enabled"] = settings.SYNC_ENABLED if settings is not None else True
    result["last_sync"] = getattr(request.app.state, "last_sync_time", None)
    return result
